"""Evidence 层配置（环境变量）。"""

from __future__ import annotations

import os


def is_sec_fetch_enabled() -> bool:
    """
    是否从 SEC EDGAR 在线拉取披露。
    默认启用；设置 EVIDENCE_FETCH_SEC=0|false|no|off 关闭。
    """
    val = os.environ.get("EVIDENCE_FETCH_SEC", "1").strip().lower()
    return val not in ("0", "false", "no", "off")


def sec_user_agent() -> str:
    """SEC 要求请求带可识别 User-Agent（含联系邮箱）。"""
    return os.environ.get(
        "EVIDENCE_SEC_USER_AGENT",
        "QuantResearchAgentDemo/1.0 (research@example.com)",
    ).strip()


def search_mode() -> str:
    """
    检索模式：tfidf | hybrid | embedding。
    hybrid = TF-IDF + 稠密向量加权融合（默认）。
    """
    return os.environ.get("EVIDENCE_SEARCH_MODE", "hybrid").strip().lower()


def hybrid_alpha() -> float:
    """Hybrid 检索中 embedding 分数权重（0~1，默认 0.45）。"""
    try:
        return float(os.environ.get("EVIDENCE_HYBRID_ALPHA", "0.45"))
    except ValueError:
        return 0.45
