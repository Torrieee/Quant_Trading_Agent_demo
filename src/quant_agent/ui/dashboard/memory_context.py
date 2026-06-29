"""记忆与上下文检查页面。"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ...evidence.memory_lifecycle import load_memory_meta, memory_meta_path
from ...evidence.semantic_memory import load_semantic_facts
from ...evidence import EvidenceRetriever


def render_memory_context_page() -> None:
    st.title("记忆与上下文")
    st.caption("查看 episodic / semantic / memory_meta 与检索结果（无需跑完整分析）。")

    symbol = st.text_input("标的", value="FIXTURE").strip().upper()
    query = st.text_input("检索 query", value="supply chain risk")

    c1, c2 = st.columns(2)
    with c1:
        load_btn = st.button("加载 Memory 元数据", use_container_width=True)
    with c2:
        search_btn = st.button("执行检索", use_container_width=True)

    if load_btn or search_btn:
        meta_path = memory_meta_path(symbol)
        st.subheader("Memory Meta")
        if meta_path.is_file():
            records = load_memory_meta(symbol)
            st.write(f"路径: `{meta_path}`，共 {len(records)} 条")
            st.dataframe(records, use_container_width=True)
            contradicted = [r for r in records if r.get("validation_status") == "contradicted"]
            if contradicted:
                st.warning(f"存在 {len(contradicted)} 条 contradicted 记录（检索会降权）")
        else:
            st.caption("尚无 memory_meta；请先在「分析工作台」成功跑一次分析。")

        facts = load_semantic_facts(symbol)
        st.subheader(f"Semantic Facts ({len(facts)})")
        if facts:
            st.dataframe(facts, use_container_width=True)
        else:
            st.caption("无 semantic facts")

        retriever = EvidenceRetriever.get_default()
        retriever.ensure_index(symbol, stock_info={"symbol": symbol, "sector": "Tech"})
        episodic = retriever.list_episodic(symbol, limit=5)
        st.subheader(f"Episodic Chunks ({len(episodic)})")
        for ch in episodic:
            with st.expander(ch.title or ch.doc_id):
                st.write(ch.text[:800])

    if search_btn:
        st.subheader("检索结果")
        retriever = EvidenceRetriever.get_default()
        hits = retriever.search(symbol, query, top_k=5)
        if not hits:
            st.caption("无结果")
        for h in hits:
            with st.expander(f"{h.doc_id} score={h.score}"):
                st.write(h.text[:600])

    if not load_btn and not search_btn:
        st.info("输入标的后点击「加载 Memory 元数据」或「执行检索」。")
        with st.expander("如何测 Memory 生命周期？"):
            st.markdown(
                """
1. **分析工作台** → 标的 `FIXTURE` → 任务选「供应链风险（动态 Research）」→ 跑两次相同任务  
2. 回到本页 → **加载 Memory 元数据** → 第二次应出现 `last_write_skipped` 或 meta 不重复增长  
3. 先跑 **评测中心 → E2E 回归**，其中 `mem_lifecycle_consolidation` / `mem_skip_duplicate_write` 专测 Memory  
4. **执行检索** → 验证 supply chain 相关 chunk 排在前面（RAG）  
                """
            )
