"""评测中心页面：一键跑离线 Eval。"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[4]


def _project_root() -> Path:
    return ROOT


def render_eval_page() -> None:
    st.title("评测中心")
    st.caption("在浏览器中触发与 CI 相同的离线评测（无需 API Key）。")

    col1, col2, col3 = st.columns(3)
    run_reg = col1.button("E2E 回归 (15条)", use_container_width=True, type="primary")
    run_ret = col2.button("检索评测", use_container_width=True)
    run_rel = col3.button("可靠性评测", use_container_width=True)

    run_all = st.button("运行全部（三项离线评测）", use_container_width=True)

    if not (run_reg or run_ret or run_rel or run_all):
        st.info("点击上方按钮运行评测。")
        with st.expander("各评测测什么？"):
            st.markdown(
                """
| 按钮 | 对应脚本 | 内容 |
|------|----------|------|
| E2E 回归 | `run_eval.py` | 15 条全链路：编排、RAG、Memory、动态 Research、HITL、风控 |
| 检索评测 | `run_retrieval_eval.py` | Recall@5 / MRR，tfidf vs hybrid vs rerank 消融 |
| 可靠性评测 | `run_reliability_eval.py` | 故障恢复 + 不可信文档注入 |
                """
            )
        return

    results_box = st.container()

    if run_reg or run_all:
        with st.spinner("运行 regression_v1…"):
            from quant_agent.eval.runner import AgentEvalRunner, write_eval_markdown, write_eval_report

            report = AgentEvalRunner(
                evalset_path=_project_root() / "evalsets" / "regression_v1.yaml"
            ).run_evalset()
            out = _project_root() / "reports" / "eval_regression_v1.json"
            write_eval_report(report, out)
            write_eval_markdown(report, out.with_suffix(".md"))
        with results_box:
            sc = report["scorecard"]
            s = sc["summary"]
            st.success(f"回归: {s['passed']}/{sc['case_count']} ({s['pass_rate']:.0%})")
            failed = [c for c in sc.get("cases", []) if not c["passed"]]
            if failed:
                for c in failed:
                    st.error(f"{c['name']}: {c.get('failures')}")
            with st.expander("分桶结果"):
                st.json(sc.get("by_bucket"))

    if run_ret or run_all:
        with st.spinner("运行 retrieval_v1…"):
            from quant_agent.eval.retrieval_eval import run_retrieval_eval

            rep = run_retrieval_eval(_project_root() / "evalsets" / "retrieval_v1.yaml")
            out = _project_root() / "reports" / "eval_retrieval_v1.json"
            out.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        with results_box:
            mark = "PASS" if rep["benchmark"]["passed"] else "FAIL"
            st.success(f"检索评测: {mark}")
            st.dataframe(rep.get("ablation"), use_container_width=True)

    if run_rel or run_all:
        with st.spinner("运行 reliability_v1…"):
            from quant_agent.eval.reliability import run_reliability_eval

            rep = run_reliability_eval(_project_root() / "evalsets" / "reliability_v1.yaml")
            out = _project_root() / "reports" / "eval_reliability_v1.json"
            out.write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        with results_box:
            mark = "PASS" if rep["benchmark"]["passed"] else "FAIL"
            s = rep["summary"]
            st.success(f"可靠性: {mark} — cases {s['passed_cases']}/{s['total_cases']}, pass^k={s['mean_pass_pow_k']:.0%}")
            for case in rep.get("results", []):
                st.write(f"- **{case['name']}**: {'PASS' if case['passed'] else 'FAIL'}")
