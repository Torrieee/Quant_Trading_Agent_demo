"""Agent 评测执行器：加载 evalset YAML，跑 QuantEngine 并汇总 scorecard。"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml
from langgraph.checkpoint.memory import MemorySaver

from ..agents.checkpoint import reset_checkpointer
from ..agents.nodes import document_retrieval as dr_mod
from ..engine import QuantEngine
from ..evidence import EvidenceRetriever
from ..evidence.embeddings import reset_embedding_backend
from ..evidence.models import EvidenceChunk
from ..evidence import retriever as retriever_mod
from ..agents.llm import DeepSeekConfigError, has_deepseek_api_key
from ..runtime.runner import RuntimeRunner, _load_fixture_analysis_data
from .benchmark import check_benchmark, summarize_judge_results
from .fake_model import resolve_fake_model
from .graders import evaluate_expectations
from .judge import grade_judge_scores, run_live_judge
from .scorecard import build_scorecard, merge_case_result
from .taxonomy import classify_failures

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVALSET = PROJECT_ROOT / "evalsets" / "regression_v1.yaml"
DEFAULT_LIVE_EVALSET = PROJECT_ROOT / "evalsets" / "capability_v1.yaml"


@contextmanager
def isolated_eval_env() -> Iterator[Path]:
    """评测专用隔离环境：独立 evidence 目录，关闭外网 fetch。"""
    store = PROJECT_ROOT / "reports" / "eval_runs" / uuid.uuid4().hex
    store.mkdir(parents=True, exist_ok=True)
    prev = {
        "EVIDENCE_STORE_DIR": os.environ.get("EVIDENCE_STORE_DIR"),
        "EVIDENCE_FETCH_SEC": os.environ.get("EVIDENCE_FETCH_SEC"),
        "EVIDENCE_FETCH_NEWS": os.environ.get("EVIDENCE_FETCH_NEWS"),
        "LANGGRAPH_CHECKPOINT": os.environ.get("LANGGRAPH_CHECKPOINT"),
    }
    os.environ["EVIDENCE_STORE_DIR"] = str(store)
    os.environ["EVIDENCE_FETCH_SEC"] = "0"
    os.environ["EVIDENCE_FETCH_NEWS"] = "0"
    _reset_retriever_singletons()
    try:
        yield store
    finally:
        for key, val in prev.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        _reset_retriever_singletons()
        shutil.rmtree(store, ignore_errors=True)


def _reset_retriever_singletons() -> None:
    retriever_mod._default_retriever = None
    dr_mod._retriever = None
    reset_embedding_backend()
    reset_checkpointer()


def load_evalset(path: Path | str) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"evalset 格式错误: {path}")
    return data


def _apply_setup(setup: dict[str, Any], symbol: str) -> None:
    retriever = EvidenceRetriever()
    sym = symbol.upper()
    extra_chunks: list[EvidenceChunk] = []
    for doc in setup.get("extra_docs") or []:
        text = doc.get("text", "")
        if not text:
            continue
        extra_chunks.append(
            EvidenceChunk(
                doc_id=doc.get("doc_id") or f"{sym}_eval_{uuid.uuid4().hex[:8]}",
                text=text,
                symbol=sym,
                doc_type=doc.get("doc_type", "10-K"),
                source="eval_setup",
                title=doc.get("title", "Eval setup document"),
                section=doc.get("section"),
                source_url=doc.get("source_url"),
            )
        )

    if setup.get("ensure_index", True):
        retriever.ensure_index(
            sym,
            stock_info={"symbol": sym, "sector": "Tech"},
            extra_chunks=extra_chunks or None,
        )

    for ep in setup.get("episodic") or []:
        retriever.ingest_episodic_session(
            sym,
            case_id=ep.get("case_id", f"eval_seed_{uuid.uuid4().hex[:6]}"),
            task=ep.get("task", f"Prior analysis for {sym}"),
            decision={
                "signal_type": ep.get("signal", "hold"),
                "confidence": ep.get("confidence", 65),
                "reasoning": ep.get("reasoning", "eval seed"),
            },
            risk_verdict=ep.get("risk_verdict", "pass"),
            risk_reason=None,
            report=ep.get("report", f"# Seed\n\nPrior signal: {ep.get('signal', 'hold')}"),
            final_state=ep.get("final_state") or {"recommended_strategy": "momentum"},
        )


def _build_case_payload(case: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = {**defaults, **case}
    gate = {**(defaults.get("gate") or {}), **(case.get("gate") or {})}
    merged["gate"] = gate
    if "fixture" in defaults and "fixture" not in case:
        merged["fixture"] = defaults["fixture"]
    if "symbol" in defaults and "symbol" not in case:
        merged["symbol"] = defaults["symbol"]
    return merged


class AgentEvalRunner:
    """统一评测入口：FIXTURE + fake model 回归，或 live DeepSeek。"""

    def __init__(
        self,
        *,
        model: Any | None = None,
        evalset_path: Path | str | None = None,
    ) -> None:
        self.model = model
        self.evalset_path = Path(evalset_path or DEFAULT_EVALSET)

    def run_evalset(
        self,
        path: Path | str | None = None,
        *,
        write_trace: bool = False,
        enable_judge: bool | None = None,
    ) -> dict[str, Any]:
        spec = load_evalset(path or self.evalset_path)
        evalset_id = spec.get("evalset_id", "unknown")
        defaults = spec.get("defaults") or {}
        cases = spec.get("cases") or []
        benchmark = spec.get("benchmark") or {}
        use_fake = (spec.get("model") or "fake").lower() != "live"
        mode = "offline" if use_fake else "live"

        if not use_fake and self.model is None and not has_deepseek_api_key():
            raise DeepSeekConfigError(
                "Live 评测需要 DEEPSEEK_API_KEY。请设置环境变量后重试。"
            )

        judge_on = enable_judge
        if judge_on is None:
            judge_on = bool(benchmark.get("judge")) and not use_fake

        results: list[dict[str, Any]] = []
        with isolated_eval_env():
            for case in cases:
                results.append(
                    self._run_single_case(
                        case,
                        defaults,
                        use_fake=use_fake,
                        write_trace=write_trace,
                        enable_judge=judge_on,
                        benchmark=benchmark,
                    )
                )

        scorecard = build_scorecard(evalset_id, results, mode=mode)
        judge_summary = summarize_judge_results(results) if judge_on else None
        benchmark_result = check_benchmark(
            scorecard,
            benchmark,
            judge_summary=judge_summary,
        )
        return {
            "evalset": spec,
            "scorecard": scorecard,
            "results": results,
            "judge_summary": judge_summary,
            "benchmark": benchmark_result,
        }

    def _run_single_case(
        self,
        case: dict[str, Any],
        defaults: dict[str, Any],
        *,
        use_fake: bool,
        write_trace: bool,
        enable_judge: bool = False,
        benchmark: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _build_case_payload(case, defaults)
        name = payload["name"]
        tags = list(payload.get("tags") or [])
        expect = payload.get("expect") or {}
        setup = payload.get("setup") or {}
        symbol = payload.get("symbol", "FIXTURE")
        benchmark = benchmark or {}

        if setup:
            _apply_setup(setup, symbol)

        case_type = (payload.get("type") or "runtime").lower()
        if case_type == "hitl":
            raw = self._run_hitl_case(payload, use_fake=use_fake)
        else:
            model = self.model
            if model is None and use_fake:
                model = resolve_fake_model(payload.get("fake_model"))
            runner = RuntimeRunner(model=model)
            raw = runner.run_case(payload, write_trace=write_trace)

        if not use_fake and self.model is None:
            raw.setdefault("mode", "live")

        expect_grade = evaluate_expectations(raw, expect)
        merged = merge_case_result(raw, expect_grade=expect_grade, tags=tags)

        run_judge = enable_judge and (case.get("judge") or benchmark.get("judge"))
        if run_judge and not use_fake:
            judge_result = run_live_judge(
                payload,
                merged.get("trace") or {},
                rule_evaluations=merged.get("evaluations") or {},
            )
            min_score = int(
                case.get("judge_min_score")
                or benchmark.get("judge_min_score")
                or 3
            )
            require_judge = bool(
                case.get("require_judge", benchmark.get("require_judge", False))
            )
            judge_grade = grade_judge_scores(
                judge_result,
                min_score=min_score,
                require_judge=require_judge,
            )
            merged["evaluations"] = {
                **(merged.get("evaluations") or {}),
                "llm_judge": judge_result,
                "judge_grade": judge_grade,
            }
            if require_judge and judge_grade.get("failures"):
                merged["failures"] = list(merged.get("failures") or []) + judge_grade[
                    "failures"
                ]
                merged["passed"] = len(merged["failures"]) == 0
                merged["failure_tags"] = classify_failures(merged["failures"])

        if not merged.get("passed"):
            try:
                from ..observability.trace_analysis import ingest_eval_failure

                trace_steps = (merged.get("trace") or {}).get("steps") or []
                merged["trace_insight"] = ingest_eval_failure(
                    case_id=name,
                    failures=list(merged.get("failures") or []),
                    trace_steps=trace_steps,
                    extra={"symbol": symbol, "source": "eval_runner"},
                )
            except Exception:
                pass

        return merged

    def _run_hitl_case(self, case: dict[str, Any], *, use_fake: bool) -> dict[str, Any]:
        """HITL：analyze 中断 → resume 完成。"""
        name = case["name"]
        symbol = case.get("symbol", "FIXTURE")
        gate = dict(case.get("gate") or {})
        gate["require_human_approval"] = True
        task = case.get("task") or name
        flags = case.get("workflow_flags") or {}

        model = self.model if not use_fake else resolve_fake_model(case.get("fake_model"))
        analysis_data = case.get("analysis_data")
        if analysis_data is None and case.get("fixture"):
            analysis_data = _load_fixture_analysis_data(case["fixture"], symbol)

        os.environ["LANGGRAPH_CHECKPOINT"] = "memory"
        _reset_retriever_singletons()
        cp = MemorySaver()
        engine = QuantEngine(model=model, checkpointer=cp, enable_checkpoint=True)

        phase1 = engine.analyze(
            symbol,
            task=task,
            gate=gate,
            analysis_data=analysis_data,
            case_id=name,
            thread_id=name,
            include_fundamental=flags.get("include_fundamental", True),
            include_sentiment=flags.get("include_sentiment", True),
            include_research_analyst=flags.get("include_research_analyst", True),
            enable_reflection=flags.get("enable_reflection", False),
            export_trace=False,
        )

        expect_after = (case.get("expect_after_resume") or case.get("expect") or {})
        if case.get("expect_interrupt"):
            grade_interrupt = evaluate_expectations(
                {
                    "case_id": name,
                    "passed": phase1.interrupted,
                    "failures": [] if phase1.interrupted else ["expect: 未 interrupt"],
                    "interrupted": phase1.interrupted,
                    "final_state": phase1.final_state,
                    "preliminary_decision": phase1.decision,
                    "risk_verdict": phase1.risk_verdict,
                    "agents_visited": phase1.agents_visited,
                    "trace": {"steps": phase1.trace_steps},
                    "step_count": len(phase1.trace_steps),
                },
                case.get("expect_interrupt") or {"interrupted": True},
            )
            if not grade_interrupt["passed"]:
                return {
                    "case_id": name,
                    "passed": False,
                    "failures": grade_interrupt["failures"],
                    "interrupted": phase1.interrupted,
                    "final_state": phase1.final_state,
                    "preliminary_decision": phase1.decision,
                    "risk_verdict": phase1.risk_verdict,
                    "agents_visited": phase1.agents_visited,
                    "report": phase1.report,
                    "trace": {"steps": phase1.trace_steps},
                    "step_count": len(phase1.trace_steps),
                    "evaluations": {"interrupt_phase": grade_interrupt},
                }

        phase2 = engine.resume(
            symbol,
            case_id=name,
            thread_id=name,
            human_approval=case.get("human_approval", "pass"),
            submit_paper_trade=False,
        )

        failures: list[str] = []
        if not phase2.report and gate.get("expect_report", True):
            failures.append("runtime: 缺少报告")
        for agent in gate.get("expected_agents") or []:
            if agent not in phase2.agents_visited:
                failures.append(f"runtime: 缺少预期智能体 '{agent}'")

        raw = {
            "case_id": name,
            "passed": len(failures) == 0,
            "failures": failures,
            "interrupted": False,
            "final_state": phase2.final_state,
            "preliminary_decision": phase2.decision,
            "risk_verdict": phase2.risk_verdict,
            "agents_visited": phase2.agents_visited,
            "report": phase2.report,
            "trace": {"steps": phase2.trace_steps},
            "step_count": len(phase2.trace_steps),
            "evaluations": {
                "hitl_phase1_interrupted": phase1.interrupted,
            },
        }
        if expect_after:
            extra = evaluate_expectations(raw, expect_after)
            raw["failures"].extend(extra["failures"])
            raw["passed"] = len(raw["failures"]) == 0
            raw["evaluations"]["expect_after_resume"] = extra
        return raw


def write_eval_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def write_eval_markdown(report: dict[str, Any], path: Path) -> None:
    sc = report["scorecard"]
    s = sc["summary"]
    lines = [
        f"# Agent Eval — {sc['evalset_id']}",
        "",
        f"- **模式**: {sc['mode']}",
        f"- **通过率**: {s['passed']}/{sc['case_count']} ({s['pass_rate']:.0%})",
        f"- **平均步数**: {s['mean_steps']}",
        "",
        "## 分桶结果",
        "",
        "| 能力域 | 通过/总数 | 通过率 |",
        "|--------|-----------|--------|",
    ]
    for bucket, stats in sorted(sc.get("by_bucket", {}).items()):
        lines.append(
            f"| {bucket} | {stats['passed']}/{stats['total']} | {stats['pass_rate']:.0%} |"
        )
    if sc.get("failure_tags"):
        lines.extend(["", "## Failure Tags", ""])
        for tag, count in sorted(sc["failure_tags"].items(), key=lambda x: -x[1]):
            lines.append(f"- `{tag}`: {count}")
    judge_summary = report.get("judge_summary")
    if judge_summary and judge_summary.get("judged_cases"):
        lines.extend(["", "## LLM Judge 汇总", ""])
        lines.append(f"- 已评判 case 数: {judge_summary['judged_cases']}")
        if judge_summary.get("mean_overall") is not None:
            lines.append(f"- 均分: {judge_summary['mean_overall']}")
        for dim, val in (judge_summary.get("dimension_means") or {}).items():
            if val is not None:
                lines.append(f"- {dim}: {val}")
    bench = report.get("benchmark")
    if bench:
        lines.extend(["", "## Benchmark", ""])
        mark = "PASS" if bench.get("passed") else "FAIL"
        lines.append(f"- 门槛检查: **{mark}**")
        for f in bench.get("failures") or []:
            lines.append(f"  - {f}")
    lines.extend(["", "## Cases", ""])
    for c in sc.get("cases", []):
        mark = "PASS" if c["passed"] else "FAIL"
        lines.append(f"- **{c['name']}** [{mark}] tags={c.get('tags')}")
        if c.get("failures"):
            for f in c["failures"]:
                lines.append(f"  - {f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
