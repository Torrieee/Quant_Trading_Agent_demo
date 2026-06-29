"""披露文本层次分块（SEC / 长文档）。"""

from __future__ import annotations

import re

from .models import EvidenceChunk

# SEC 10-K / 10-Q 常见 Item 标题
_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Item 1A Risk Factors", re.compile(r"(?i)item\s*1a[\.\s\-–—]*risk\s*factors")),
    ("Item 1 Business", re.compile(r"(?i)item\s*1[\.\s\-–—]*business")),
    ("Item 7 MD&A", re.compile(r"(?i)item\s*7[\.\s\-–—]*management")),
    ("Item 2.02 Results", re.compile(r"(?i)item\s*2\.02")),
]


def _chunk_id(symbol: str, section: str, idx: int) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", section).strip("_") or "section"
    return f"{symbol.upper()}_SEC_{safe}_{idx}"


def split_filing_text(
    symbol: str,
    text: str,
    *,
    form: str,
    source: str = "sec_edgar",
    source_url: str | None = None,
    published_at: str | None = None,
    max_section_chars: int = 2500,
    fallback_chars: int = 4000,
) -> list[EvidenceChunk]:
    """
    按 Item 分段；无法识别时按固定窗口滑动分块。
    """
    sym = symbol.upper()
    if not text or len(text.strip()) < 200:
        return []

    lower = text.lower()
    boundaries: list[tuple[int, str]] = []
    for label, pattern in _SECTION_PATTERNS:
        m = pattern.search(lower)
        if m:
            boundaries.append((m.start(), label))
    boundaries.sort(key=lambda x: x[0])

    chunks: list[EvidenceChunk] = []
    if boundaries:
        for i, (start, label) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            section_text = text[start:end].strip()[:max_section_chars]
            if len(section_text) < 120:
                continue
            chunks.append(
                EvidenceChunk(
                    doc_id=_chunk_id(sym, label, i),
                    text=section_text,
                    symbol=sym,
                    doc_type=form,
                    source=source,
                    title=f"{sym} {form} — {label}",
                    published_at=published_at,
                    source_url=source_url,
                    section=label,
                )
            )
        if chunks:
            return chunks

    # 滑动窗口 fallback
    step = max(800, fallback_chars // 2)
    idx = 0
    for start in range(0, len(text), step):
        part = text[start : start + fallback_chars].strip()
        if len(part) < 200:
            break
        chunks.append(
            EvidenceChunk(
                doc_id=_chunk_id(sym, "excerpt", idx),
                text=part,
                symbol=sym,
                doc_type=form,
                source=source,
                title=f"{sym} {form} excerpt #{idx + 1}",
                published_at=published_at,
                source_url=source_url,
                section="filing_excerpt",
            )
        )
        idx += 1
        if idx >= 4:
            break
    return chunks
