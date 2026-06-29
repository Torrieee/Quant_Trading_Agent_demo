"""分析工作台页面。"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from ...engine import QuantEngine
from ..demo_model import DemoChatModel, load_fixture_analysis_data
from ..evidence import build_evidence_view

SIGNAL_COLORS = {
    "buy": "#16a34a",
    "sell": "#dc2626",
    "hold": "#ca8a04",
}

TASK_PRESETS = {
    "默认综合": "评估当前是否适合建仓，并给出策略与仓位建议",
    "供应链风险（动态 Research）": "评估 FIXTURE 供应链与亚洲制造集中风险，推荐策略并完成风控",
    "震荡市策略": "震荡市下为 FIXTURE 推荐策略并完成风控与报告",
    "历史记忆召回": "结合历史分析记录，评估 FIXTURE 当前应延续还是调整策略",
}


def _render_signal_badge(signal_type: str, confidence: float | int | None) -> None:
    color = SIGNAL_COLORS.get(str(signal_type).lower(), "#64748b")
    conf = confidence if confidence is not None else "—"
    st.markdown(
        f'<div style="display:inline-block;padding:0.35rem 0.9rem;border-radius:999px;'
        f'background:{color}22;color:{color};font-weight:700;">'
        f"{str(signal_type).upper()} · 置信度 {conf}%</div>",
        unsafe_allow_html=True,
    )


def _run_analysis(
    *,
    symbol: str,
    task: str,
    demo_mode: bool,
    include_fundamental: bool,
    include_sentiment: bool,
    include_research_analyst: bool,
    enable_dynamic_research: bool,
    enable_reflection: bool,
    require_hitl: bool,
    max_position: float | None,
    context_budget: int,
) -> Any:
    prev_budget = os.environ.get("AGENT_CONTEXT_BUDGET")
    os.environ["AGENT_CONTEXT_BUDGET"] = str(context_budget)
    if require_hitl:
        os.environ["LANGGRAPH_CHECKPOINT"] = "memory"
    try:
        gate: dict[str, Any] = {}
        if require_hitl:
            gate["require_human_approval"] = True
        if max_position is not None:
            gate["max_position_size"] = max_position

        sym = symbol.strip().upper() or "FIXTURE"
        if demo_mode:
            analysis_data = load_fixture_analysis_data("FIXTURE")
            analysis_data["stock_info"] = {**analysis_data["stock_info"], "symbol": sym}
            engine = QuantEngine(
                model=DemoChatModel(),
                enable_checkpoint=True if require_hitl else None,
            )
        else:
            engine = QuantEngine(enable_checkpoint=True if require_hitl else None)
            analysis_data = None

        return engine.analyze(
            sym,
            task=task or None,
            include_fundamental=include_fundamental,
            include_sentiment=include_sentiment,
            include_research_analyst=include_research_analyst,
            enable_reflection=enable_reflection,
            enable_dynamic_research=enable_dynamic_research,
            analysis_data=analysis_data,
            gate=gate or None,
            case_id="dashboard_analyze",
            thread_id="dashboard_analyze",
        )
    finally:
        if prev_budget is None:
            os.environ.pop("AGENT_CONTEXT_BUDGET", None)
        else:
            os.environ["AGENT_CONTEXT_BUDGET"] = prev_budget


def render_analysis_page(*, has_api_key: bool) -> None:
    st.title("分析工作台")
    st.caption("运行 QuantEngine 全链路，测试 ReAct / 动态 Research / HITL / Context / Memory 写入。")

    with st.sidebar:
        st.header("标的与任务")
        symbol = st.text_input("股票代码", value="FIXTURE", help="Demo 推荐 FIXTURE；在线可用 AAPL")
        preset = st.selectbox("任务预设", list(TASK_PRESETS.keys()))
        task = st.text_area("分析任务", value=TASK_PRESETS[preset], height=80)

        st.divider()
        st.markdown("**工作流开关**")
        include_fundamental = st.checkbox("基本面", value=True)
        include_sentiment = st.checkbox("情绪", value=True)
        include_research_analyst = st.checkbox("研究分析师（规则）", value=True)
        enable_dynamic = st.checkbox(
            "动态 Research 子图",
            value=("供应链" in task or "供应链" in preset),
            help="Planner → Workers → Verifier → Synthesizer",
        )
        enable_reflection = st.checkbox("Reflection 检查", value=False)
        require_hitl = st.checkbox("HITL（Risk 前人工审批）", value=False)

        st.divider()
        st.markdown("**高级**")
        context_budget = st.number_input("Context token 预算", min_value=2000, max_value=32000, value=8000, step=500)
        max_pos = st.slider("仓位上限 (gate)", 0.05, 1.0, 1.0, 0.05)

        st.divider()
        demo_mode = st.toggle("Demo 模式（无需 API Key）", value=not has_api_key)
        if not demo_mode and not has_api_key:
            st.warning("未配置 DEEPSEEK_API_KEY，请开启 Demo 或配置 .env")

        run_btn = st.button("开始分析", type="primary", use_container_width=True)

    # HITL resume from session
    if st.session_state.get("hitl_pending"):
        st.warning("工作流在 Risk 前中断，等待人工审批。")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("批准继续", type="primary"):
                eng = QuantEngine(
                    model=DemoChatModel() if st.session_state.get("hitl_demo") else None,
                    enable_checkpoint=True,
                )
                sym = st.session_state.get("hitl_symbol", "FIXTURE")
                res = eng.resume(sym, case_id="dashboard_analyze", thread_id="dashboard_analyze", human_approval="pass")
                st.session_state["last_result"] = res
                st.session_state["hitl_pending"] = False
                st.rerun()
        with c2:
            if st.button("拒绝"):
                eng = QuantEngine(
                    model=DemoChatModel() if st.session_state.get("hitl_demo") else None,
                    enable_checkpoint=True,
                )
                sym = st.session_state.get("hitl_symbol", "FIXTURE")
                res = eng.resume(sym, case_id="dashboard_analyze", thread_id="dashboard_analyze", human_approval="reject")
                st.session_state["last_result"] = res
                st.session_state["hitl_pending"] = False
                st.rerun()
        return

    if not run_btn and "last_result" not in st.session_state:
        st.info("配置左侧参数后点击「开始分析」。")
        with st.expander("本页可测什么？"):
            st.markdown(
                """
| 开关 | 测什么 |
|------|--------|
| Demo 模式 | 离线 fixture + 假 LLM，无需 API |
| 动态 Research | `research_planner` / workers / verifier 子图 |
| Reflection | 研究产出字段完整性检查 |
| HITL | Risk 前 interrupt + 本页审批继续 |
| Context 预算 | `context_manifest` 打包与截断 |
| FIXTURE + 供应链任务 | RAG + 动态 evidence worker |

分析成功后可在 **记忆与上下文** 页查看 episodic / memory_meta。
                """
            )
        return

    if run_btn:
        if not symbol.strip():
            st.error("请输入股票代码")
            return
        with st.spinner("运行 LangGraph 工作流…"):
            result = _run_analysis(
                symbol=symbol.strip(),
                task=task.strip(),
                demo_mode=demo_mode,
                include_fundamental=include_fundamental,
                include_sentiment=include_sentiment,
                include_research_analyst=include_research_analyst,
                enable_dynamic_research=enable_dynamic,
                enable_reflection=enable_reflection,
                require_hitl=require_hitl,
                max_position=max_pos if max_pos < 1.0 else None,
                context_budget=int(context_budget),
            )
        st.session_state["last_result"] = result
        st.session_state["analysis_options"] = {
            "enable_dynamic": enable_dynamic,
            "demo_mode": demo_mode,
        }
        if result.interrupted:
            st.session_state["hitl_pending"] = True
            st.session_state["hitl_symbol"] = result.symbol
            st.session_state["hitl_demo"] = demo_mode
            st.rerun()

    result = st.session_state.get("last_result")
    if result is None:
        return

    evidence = build_evidence_view(result)
    fs = result.final_state or {}

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("成功", "是" if result.success else "否")
    m2.metric("风控", result.risk_verdict or "—")
    m3.metric("步数", len(result.trace_steps))
    opts = st.session_state.get("analysis_options") or {}
    m4.metric("Research 模式", "动态子图" if opts.get("enable_dynamic") else "ReAct")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["结论", "Trace 时间线", "Research / Context", "报告", "原始 JSON"]
    )

    with tab1:
        decision = result.decision or {}
        _render_signal_badge(decision.get("signal_type", "—"), decision.get("confidence"))
        if decision.get("reasoning"):
            st.info(decision["reasoning"])
        for item in evidence.get("conclusion_bindings", []):
            with st.container(border=True):
                st.markdown(f"**{item['conclusion_key']}**: {item['value']}")
                st.caption(item.get("description") or "")

    with tab2:
        for step in evidence.get("timeline", []):
            title = f"#{step['step_id']} {step['agent_label']} / {step['tool_label']} ({step['status']})"
            with st.expander(title):
                if step.get("rationale"):
                    st.write(step["rationale"])
                st.json(step.get("observation") or {})

    with tab3:
        if fs.get("research_findings"):
            st.subheader("动态 Research Findings")
            st.json(fs["research_findings"])
        if fs.get("research_verification"):
            st.subheader("Verifier")
            ver = fs["research_verification"]
            st.write("通过" if ver.get("passed") else "未通过", ver)
        manifest = fs.get("context_manifest")
        if manifest:
            st.subheader("Context Manifest")
            st.json(manifest)
        if fs.get("memory_lifecycle"):
            st.subheader("Memory 写入")
            st.json(fs["memory_lifecycle"])
        if fs.get("episodic_memory"):
            st.subheader(f"Episodic 检索 ({len(fs['episodic_memory'])} 条)")
            st.json(fs["episodic_memory"][:3])

    with tab4:
        if result.report:
            st.markdown(result.report)
        else:
            st.caption("无报告")

    with tab5:
        st.json(
            {
                "agents_visited": result.agents_visited,
                "decision": result.decision,
                "final_state": fs,
                "trace_steps": result.trace_steps,
            }
        )
