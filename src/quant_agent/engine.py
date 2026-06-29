"""多智能体投资分析引擎（DeepSeek API 在线模式）。"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Iterator

from .agents.coordinator import AgentCoordinator
from .agents.llm import require_deepseek_chat_model
from .compliance.audit_log import append_audit_record
from .compliance.guardrails import validate_decision
from .config import DataConfig
from .data import download_ohlcv, get_stock_info
from .evidence import EvidenceRetriever
from .execution.paper_trading import submit_paper_order
from .harness.tool_adapter import HarnessToolAdapter


@dataclass
class EngineResult:
    """QuantEngine.analyze 统一返回结构。"""

    symbol: str
    success: bool
    decision: dict[str, Any]
    individual_signals: dict[str, Any]
    risk_verdict: str | None
    risk_reason: str | None
    report: str | None
    final_state: dict[str, Any]
    trace_steps: list[dict[str, Any]]
    agents_visited: list[str]
    error: str | None = None
    interrupted: bool = False
    interrupt_at: str | None = None
    compliance_warnings: list[str] = field(default_factory=list)
    paper_order: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_workflow(cls, symbol: str, state: dict[str, Any], *, coordinator: AgentCoordinator | None = None, case_id: str = "") -> EngineResult:
        quant = dict(state.get("quant_state") or {})
        prelim = state.get("preliminary_decision") or quant.get("preliminary_decision") or {}
        interrupted = False
        interrupt_at = None
        if coordinator and case_id:
            interrupted = coordinator.is_interrupted(case_id, thread_id=case_id)
            if interrupted:
                interrupt_at = "risk"
        warnings = list(state.get("compliance_warnings") or [])
        warnings.extend(validate_decision(prelim))
        return cls(
            symbol=symbol,
            success=True,
            decision=prelim,
            individual_signals=dict(state.get("individual_signals") or quant.get("individual_signals") or {}),
            risk_verdict=state.get("risk_verdict"),
            risk_reason=state.get("risk_reason"),
            report=state.get("report"),
            final_state=quant,
            trace_steps=list(state.get("trace_steps") or []),
            agents_visited=list(state.get("agents_visited") or []),
            interrupted=interrupted,
            interrupt_at=interrupt_at,
            compliance_warnings=warnings,
            raw=state,
        )


class QuantEngine:
    """金融投资多智能体引擎 — 需 DeepSeek API 或注入 model。"""

    def __init__(
        self,
        *,
        adapter: HarnessToolAdapter | None = None,
        model: Any | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
        checkpointer: Any | None = None,
        enable_checkpoint: bool | None = None,
    ) -> None:
        self.evidence_retriever = evidence_retriever or EvidenceRetriever.get_default()
        if adapter is None:
            from .llm_agent import TradingFunctionCaller

            adapter = HarnessToolAdapter(
                TradingFunctionCaller(evidence_retriever=self.evidence_retriever)
            )
        self.adapter = adapter
        self.model = model
        self.coordinator = AgentCoordinator(
            adapter=self.adapter,
            model=model,
            checkpointer=checkpointer,
            enable_checkpoint=enable_checkpoint,
        )

    def _resolve_model(self) -> Any:
        if self.model is not None:
            return self.model
        return require_deepseek_chat_model()

    def analyze(
        self,
        symbol: str,
        *,
        task: str | None = None,
        gate: dict[str, Any] | None = None,
        start: dt.date | None = None,
        include_fundamental: bool = True,
        include_sentiment: bool = True,
        include_research_analyst: bool = True,
        enable_reflection: bool = False,
        analysis_data: dict[str, Any] | None = None,
        case_id: str = "engine_analyze",
        thread_id: str | None = None,
        submit_paper_trade: bool = False,
        export_trace: bool = True,
    ) -> EngineResult:
        """综合分析标的；Research / Risk / Reporter 均通过 API 调用大模型。"""
        task_text = task or f"分析 {symbol} 并给出投资建议与仓位方案"
        gate = gate or {}

        try:
            model = self._resolve_model()
            self.coordinator.model = model

            if analysis_data is None:
                start_date = start or dt.date.today() - dt.timedelta(days=365)
                historical = download_ohlcv(
                    DataConfig(symbol=symbol, start=start_date),
                    use_cache=True,
                )
                stock_info = get_stock_info(symbol)
                analysis_data = {
                    "historical_data": historical,
                    "stock_info": stock_info,
                }

            flags = {
                "include_fundamental": include_fundamental,
                "include_sentiment": include_sentiment,
                "include_research_analyst": include_research_analyst,
                "enable_reflection": enable_reflection,
            }

            tid = thread_id or case_id
            final = self.coordinator.run(
                case_id=case_id,
                symbol=symbol,
                task=task_text,
                analysis_data=analysis_data,
                gate=gate,
                workflow_flags=flags,
                thread_id=tid,
            )
            result = EngineResult.from_workflow(symbol, final, coordinator=self.coordinator, case_id=tid)
            if final.get("risk_verdict") == "reject":
                result.success = False
            if result.interrupted:
                result.success = True

            if export_trace:
                try:
                    self.coordinator.export_run_trace(case_id=case_id, symbol=symbol, state=final)
                except Exception:
                    pass

            append_audit_record(
                {
                    "case_id": case_id,
                    "symbol": symbol,
                    "decision": result.decision,
                    "risk_verdict": result.risk_verdict,
                    "interrupted": result.interrupted,
                    "compliance_warnings": result.compliance_warnings,
                }
            )

            if result.success and result.report and not result.interrupted:
                try:
                    self.evidence_retriever.ingest_episodic_session(
                        symbol,
                        case_id=case_id,
                        task=task_text,
                        decision=result.decision,
                        risk_verdict=result.risk_verdict,
                        risk_reason=result.risk_reason,
                        report=result.report,
                        final_state=result.final_state,
                    )
                except Exception:
                    pass

            if submit_paper_trade and result.success and not result.interrupted:
                result.paper_order = self._maybe_paper_trade(symbol, result, case_id=case_id)

            return result
        except Exception as exc:
            return EngineResult(
                symbol=symbol,
                success=False,
                decision={},
                individual_signals={},
                risk_verdict=None,
                risk_reason=None,
                report=None,
                final_state={},
                trace_steps=[],
                agents_visited=[],
                error=str(exc),
            )

    def resume(
        self,
        symbol: str,
        *,
        case_id: str,
        thread_id: str | None = None,
        human_approval: str = "pass",
        submit_paper_trade: bool = False,
    ) -> EngineResult:
        """HITL：人工审批后继续 workflow（需 checkpoint + require_human_approval）。"""
        tid = thread_id or case_id
        final = self.coordinator.resume(case_id, thread_id=tid, human_approval=human_approval)
        result = EngineResult.from_workflow(symbol, final, coordinator=self.coordinator, case_id=tid)
        if final.get("risk_verdict") == "reject":
            result.success = False
        if result.success and result.report:
            try:
                self.evidence_retriever.ingest_episodic_session(
                    symbol,
                    case_id=case_id,
                    task=str(final.get("task") or ""),
                    decision=result.decision,
                    risk_verdict=result.risk_verdict,
                    risk_reason=result.risk_reason,
                    report=result.report,
                    final_state=result.final_state,
                )
            except Exception:
                pass
        if submit_paper_trade and result.success:
            result.paper_order = self._maybe_paper_trade(symbol, result, case_id=case_id)
        return result

    def analyze_stream(self, symbol: str, **kwargs) -> Iterator[dict[str, Any]]:
        """流式返回 LangGraph updates（供 UI / API）。"""
        kwargs.setdefault("export_trace", False)
        task_text = kwargs.get("task") or f"分析 {symbol} 并给出投资建议与仓位方案"
        case_id = kwargs.get("case_id") or "engine_analyze"
        tid = kwargs.get("thread_id") or case_id
        gate = kwargs.get("gate") or {}
        flags = {
            "include_fundamental": kwargs.get("include_fundamental", True),
            "include_sentiment": kwargs.get("include_sentiment", True),
            "include_research_analyst": kwargs.get("include_research_analyst", True),
            "enable_reflection": kwargs.get("enable_reflection", False),
        }
        analysis_data = kwargs.get("analysis_data")
        if analysis_data is None:
            historical = download_ohlcv(
                DataConfig(symbol=symbol, start=dt.date.today() - dt.timedelta(days=365)),
                use_cache=True,
            )
            analysis_data = {"historical_data": historical, "stock_info": get_stock_info(symbol)}
        self.coordinator.model = self._resolve_model()
        yield from self.coordinator.run_stream(
            case_id=case_id,
            symbol=symbol,
            task=task_text,
            analysis_data=analysis_data,
            gate=gate,
            workflow_flags=flags,
            thread_id=tid,
        )

    def _maybe_paper_trade(self, symbol: str, result: EngineResult, *, case_id: str) -> dict[str, Any] | None:
        sig = str(result.decision.get("signal_type", "hold")).lower()
        if sig not in ("buy", "sell"):
            return None
        price = result.final_state.get("current_price") or result.final_state.get("last_price")
        if not price:
            try:
                info = get_stock_info(symbol)
                price = info.get("current_price")
            except Exception:
                return None
        qty = float(result.final_state.get("position_size") or 0.01) * 100
        if qty <= 0:
            qty = 1.0
        return submit_paper_order(symbol, sig, qty, float(price), case_id=case_id)
