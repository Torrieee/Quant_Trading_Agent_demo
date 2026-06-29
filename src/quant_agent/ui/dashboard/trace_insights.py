"""Trace 洞察页面：失败聚类、taxonomy、showcase 演示。"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[4]


def render_trace_insights_page() -> None:
    st.title("Trace 洞察")
    st.caption("失败聚类、taxonomy 归因与韧性演示链路。")

    col1, col2 = st.columns(2)
    if col1.button("扫描 trace 目录", type="primary", use_container_width=True):
        with st.spinner("分析中…"):
            from quant_agent.observability.trace_analysis import analyze_traces, write_trace_insights_report

            report = analyze_traces(ROOT / "data_cache" / "traces")
            write_trace_insights_report(report, ROOT / "reports" / "trace_insights.json")
        st.session_state["trace_report"] = report

    if col2.button("生成 Showcase trace", use_container_width=True):
        with st.spinner("运行 showcase_resilience…"):
            from quant_agent.observability.showcase import run_showcase_resilience

            result = run_showcase_resilience(project_root=ROOT, export=True)
        st.session_state["showcase_result"] = result
        st.session_state["trace_report"] = None

    report = st.session_state.get("trace_report")
    insights_path = ROOT / "reports" / "trace_insights.json"
    if report is None and insights_path.is_file():
        report = json.loads(insights_path.read_text(encoding="utf-8"))

    if report:
        s = report.get("summary") or {}
        m1, m2, m3 = st.columns(3)
        m1.metric("Trace 数", s.get("trace_count", 0))
        m2.metric("含失败", s.get("traces_with_failures", 0))
        m3.metric("失败率", f"{s.get('failure_rate', 0):.0%}")

        st.subheader("失败 Tag 聚类")
        tags = s.get("top_failure_tags") or []
        if tags:
            st.bar_chart({t["tag"]: t["count"] for t in tags})
        else:
            st.info("暂无失败 tag。")

        st.subheader("事件统计")
        events = s.get("top_events") or []
        if events:
            st.dataframe(events, use_container_width=True)

        st.subheader("闭环建议")
        for rec in report.get("recommendations") or []:
            st.write(f"- {rec}")

        with st.expander("Case 列表"):
            st.dataframe(report.get("cases") or [], use_container_width=True)

    showcase = st.session_state.get("showcase_result")
    if showcase is None:
        summary = ROOT / "reports" / "showcase_resilience_summary.json"
        if summary.is_file():
            showcase = json.loads(summary.read_text(encoding="utf-8"))

    if showcase:
        st.divider()
        st.subheader("Showcase：timeout → retry → replan → HITL → resume")
        extra = showcase.get("extra") or {}
        for line in extra.get("narrative") or []:
            st.write(line)
        if showcase.get("trace_path"):
            st.code(showcase["trace_path"])
        with st.expander("Showcase trace steps"):
            st.json(showcase.get("trace_steps", [])[:30])

    if not report and not showcase:
        st.info("点击「扫描 trace 目录」或「生成 Showcase trace」开始。")
