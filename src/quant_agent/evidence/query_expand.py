"""检索 query 扩展（同义词 / 风险短语）。"""

from __future__ import annotations

# 金融披露常见 paraphrase → 锚词
_EXPANSION_TERMS: dict[str, list[str]] = {
    "supply": ["supply chain", "vendor", "manufacturing", "single source"],
    "chain": ["supply chain", "logistics", "sourcing"],
    "risk": ["risk factors", "material adverse", "uncertainty"],
    "regulatory": ["regulation", "sec", "investigation", "compliance"],
    "bankruptcy": ["going concern", "chapter 11", "liquidity"],
    "concern": ["going concern", "substantial doubt"],
    "revenue": ["sales", "top line", "growth", "demand"],
    "profit": ["margin", "earnings", "operating income"],
}


def expand_query(query: str, *, max_variants: int = 4) -> list[str]:
    """生成若干检索变体；首项为原 query。"""
    base = query.strip()
    if not base:
        return []

    variants: list[str] = [base]
    tokens = [t.lower() for t in base.split() if len(t) > 2]
    extras: list[str] = []
    for tok in tokens:
        for phrase in _EXPANSION_TERMS.get(tok, []):
            if phrase.lower() not in base.lower():
                extras.append(f"{base} {phrase}")

    for v in extras:
        if v not in variants:
            variants.append(v)
        if len(variants) >= max_variants:
            break
    return variants
