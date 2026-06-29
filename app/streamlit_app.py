"""Quant Trading Agent — Streamlit 多页面控制台."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_agent.ui.dashboard import (  # noqa: E402
    render_analysis_page,
    render_eval_page,
    render_memory_context_page,
    render_trace_insights_page,
)

st.set_page_config(
    page_title="Quant Agent 控制台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


def main() -> None:
    _load_env_file()

    pages = st.navigation(
        [
            st.Page(lambda: render_analysis_page(has_api_key=_has_api_key()), title="分析工作台", icon="🔬"),
            st.Page(render_eval_page, title="评测中心", icon="✅"),
            st.Page(render_memory_context_page, title="记忆与上下文", icon="🧠"),
            st.Page(render_trace_insights_page, title="Trace 洞察", icon="📈"),
        ]
    )
    pages.run()


if __name__ == "__main__":
    main()
