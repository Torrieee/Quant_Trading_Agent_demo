"""Quant Trading Agent — Streamlit 可视化分析平台."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_agent.engine import QuantEngine
from quant_agent.ui import (
    DemoChatModel,
    build_evidence_view,
    load_fixture_analysis_data,
)

st.set_page_config(
    page_title="Quant Agent 分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

SIGNAL_COLORS = {
    "buy": "#16a34a",
    "sell": "#dc2626",
    "hold": "#ca8a04",
}


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _has_api_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def _render_signal_badge(signal_type: str, confidence: float | int | None) -> None:
    color = SIGNAL_COLORS.get(str(signal_type).lower(), "#64748b")
    conf = confidence if confidence is not None else "—"
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.35rem 0.9rem;
            border-radius:999px;
            background:{color}22;
            color:{color};
            font-weight:700;
            font-size:1.1rem;
        ">
            {str(signal_type).upper()} · 置信度 {conf}%
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_conclusion_section(result, evidence: dict) -> None:
    st.subheader("分析结论")
    decision = result.decision or {}
    cols = st.columns(4)
    with cols[0]:
        st.metric("标的", result.symbol)
    with cols[1]:
        _render_signal_badge(decision.get("signal_type", "—"), decision.get("confidence"))
    with cols[2]:
        st.metric("风控", result.risk_verdict or "—")
    with cols[3]:
        pos = result.final_state.get("position_size")
        st.metric("建议仓位", f"{pos:.2%}" if isinstance(pos, (int, float)) else (pos or "—"))

    if decision.get("reasoning"):
        st.info(decision["reasoning"])

    if result.error:
        st.error(result.error)
        return

    st.markdown("#### 结论与信息来源对应")
    for item in evidence.get("conclusion_bindings", []):
        with st.container(border=True):
            st.markdown(f"**{item['conclusion_key']}**")
            st.write(item["value"])
            st.caption(item.get("description") or "")
            step_ids = item.get("source_step_ids") or []
            if step_ids:
                st.markdown(
                    "来源步骤: "
                    + ", ".join(f"`#{sid}`" for sid in step_ids)
                )


def _render_signals_section(result) -> None:
    st.subheader("各分析师信号")
    signals = result.individual_signals or {}
    if not signals:
        st.caption("无 individual_signals 数据")
        return
    cols = st.columns(min(len(signals), 3))
    for idx, (name, sig) in enumerate(signals.items()):
        with cols[idx % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.write(f"信号: **{sig.get('signal_type', '—').upper()}**")
                st.write(f"置信度: {sig.get('confidence', '—')}%")
                if sig.get("reasoning"):
                    st.caption(sig["reasoning"])
                meta = sig.get("metadata") or {}
                if meta:
                    with st.expander("元数据"):
                        st.json(meta)


def _render_evidence_timeline(evidence: dict) -> None:
    st.subheader("信息来源时间线")
    st.caption("每一步对应智能体调用的工具或规则分析，observation 为原始证据。")
    timeline = evidence.get("timeline") or []
    for step in timeline:
        status = step.get("status", "ok")
        icon = "✅" if status == "ok" else "⚠️"
        title = (
            f"{icon} 步骤 #{step['step_id']} · "
            f"{step['agent_label']} / {step['tool_label']}"
        )
        with st.expander(title, expanded=step["step_id"] <= 3):
            if step.get("rationale"):
                st.write(step["rationale"])
            if step.get("arguments"):
                st.markdown("**输入参数**")
                st.json(step["arguments"])
            st.markdown("**观测结果 (observation)**")
            obs = step.get("observation")
            if obs:
                st.json(obs)
            else:
                st.caption("无 observation")
            lat = step.get("latency_ms")
            if lat:
                st.caption(f"耗时: {lat:.0f} ms")


def _render_report_section(result) -> None:
    st.subheader("综合报告")
    if result.report:
        st.markdown(result.report)
    else:
        st.caption("暂无报告")


def _run_analysis(
    symbol: str,
    task: str,
    demo_mode: bool,
    include_fundamental: bool,
    include_sentiment: bool,
    include_research_analyst: bool,
):
    if demo_mode:
        engine = QuantEngine(model=DemoChatModel())
        analysis_data = load_fixture_analysis_data(symbol)
    else:
        engine = QuantEngine()
        analysis_data = None

    return engine.analyze(
        symbol,
        task=task or None,
        include_fundamental=include_fundamental,
        include_sentiment=include_sentiment,
        include_research_analyst=include_research_analyst,
        analysis_data=analysis_data,
        case_id="dashboard_analyze",
    )


def main() -> None:
    _load_env_file()
    st.title("Quant Trading Agent 可视化平台")
    st.markdown(
        "输入标的与分析任务，系统将运行多智能体工作流并展示**结论**及可追溯的**信息来源**。"
    )

    with st.sidebar:
        st.header("输入")
        symbol = st.text_input("股票代码", value="AAPL", help="如 AAPL、MSFT、600519.SS")
        task = st.text_area(
            "分析任务（可选）",
            value="",
            placeholder="例如：评估当前是否适合建仓，并给出策略与仓位建议",
        )
        st.divider()
        st.markdown("**分析面板**")
        include_fundamental = st.checkbox("基本面分析", value=True)
        include_sentiment = st.checkbox("情绪分析", value=True)
        include_research_analyst = st.checkbox("研究分析师", value=True)
        st.divider()
        api_ok = _has_api_key()
        demo_mode = st.toggle(
            "Demo 模式（无需 API Key）",
            value=not api_ok,
            help="使用本地 fixture 数据与模拟 LLM，适合界面体验",
        )
        if not demo_mode and not api_ok:
            st.warning("未检测到 DEEPSEEK_API_KEY，请配置 .env 或开启 Demo 模式。")
        elif api_ok and not demo_mode:
            st.success("已检测到 DeepSeek API Key，将在线分析。")
        run_btn = st.button("开始分析", type="primary", use_container_width=True)

    if not run_btn:
        st.info("在左侧填写参数后点击「开始分析」。")
        with st.expander("工作流说明"):
            st.markdown(
                """
                1. **Supervisor** 协调任务  
                2. **分析面板** — Fundamental / Sentiment / ResearchAnalyst 规则分析 + 投票  
                3. **Research** — DeepSeek ReAct + 市场/策略工具  
                4. **Risk** — 仓位计算 + 规则否决  
                5. **Reporter** — 基于 trace 生成 grounded 报告  

                页面「信息来源」展示 `trace_steps` 中每步的 tool observation，并与结论字段关联。
                """
            )
        return

    if not symbol.strip():
        st.error("请输入股票代码")
        return

    with st.spinner("多智能体工作流运行中…"):
        result = _run_analysis(
            symbol.strip().upper(),
            task.strip(),
            demo_mode,
            include_fundamental,
            include_sentiment,
            include_research_analyst,
        )

    evidence = build_evidence_view(result)

    tab_conclusion, tab_signals, tab_sources, tab_report, tab_raw = st.tabs(
        ["结论", "分析师信号", "信息来源", "报告", "原始数据"]
    )

    with tab_conclusion:
        _render_conclusion_section(result, evidence)

    with tab_signals:
        _render_signals_section(result)

    with tab_sources:
        _render_evidence_timeline(evidence)
        st.divider()
        st.markdown("**访问路径**")
        st.code(" → ".join(result.agents_visited or []), language=None)

    with tab_report:
        _render_report_section(result)

    with tab_raw:
        st.json(
            {
                "decision": result.decision,
                "final_state": result.final_state,
                "trace_steps": result.trace_steps,
            }
        )


if __name__ == "__main__":
    main()
