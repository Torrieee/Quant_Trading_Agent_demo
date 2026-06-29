"""Memory 生命周期：写入决策、冲突检测、合并与失效。"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .memory import build_episodic_chunk, is_episodic_chunk
from .models import EvidenceChunk
from .semantic_memory import load_semantic_facts, merge_facts, save_semantic_facts

ValidationStatus = Literal["unverified", "verified", "contradicted"]
MemoryType = Literal["episodic", "semantic", "skip"]

LOW_SALIENCE_TTL_DAYS = 90


@dataclass
class MemoryWriteDecision:
    should_write: bool
    memory_type: MemoryType
    salience: float
    confidence: float
    reason: str
    dedup_key: str
    write_semantic: bool = False


@dataclass
class MemoryRecord:
    memory_id: str
    doc_id: str
    memory_type: str
    content: str
    source_run_id: str
    signal_type: str
    strategy: str
    confidence: float
    salience: float
    created_at: str
    validation_status: ValidationStatus = "unverified"
    expires_at: str | None = None
    supersedes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _store_dir() -> Path:
    return Path(os.environ.get("EVIDENCE_STORE_DIR", "data_cache/evidence"))


def memory_meta_path(symbol: str) -> Path:
    return _store_dir() / f"{symbol.upper()}_memory_meta.json"


def load_memory_meta(symbol: str) -> list[dict[str, Any]]:
    path = memory_meta_path(symbol)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("records") or [])
    except (json.JSONDecodeError, OSError):
        return []


def save_memory_meta(symbol: str, records: list[dict[str, Any]]) -> None:
    path = memory_meta_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"symbol": symbol.upper(), "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_signal_from_chunk(chunk: EvidenceChunk) -> tuple[str, str, float]:
    text = chunk.text
    sig_m = re.search(r"Decision:\s*(\w+)", text, re.I)
    strat_m = re.search(r"Recommended strategy:\s*(\S+)", text, re.I)
    conf_m = re.search(r"confidence\s*([\d.]+)", text, re.I)
    signal = (sig_m.group(1) if sig_m else "unknown").lower()
    strategy = (strat_m.group(1) if strat_m else "unknown").lower()
    confidence = float(conf_m.group(1)) if conf_m else 0.0
    return signal, strategy, confidence


def decide_memory_write(
    symbol: str,
    *,
    case_id: str,
    decision: dict[str, Any],
    risk_verdict: str | None,
    report: str | None,
    final_state: dict[str, Any] | None,
    recent_episodic: list[EvidenceChunk],
) -> MemoryWriteDecision:
    """规则写入决策：去重、低置信跳过 semantic、reject 降 salience。"""
    signal = str(decision.get("signal_type", "unknown")).lower()
    strategy = str((final_state or {}).get("recommended_strategy", "unknown")).lower()
    try:
        confidence = float(decision.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    dedup_key = f"{symbol.upper()}:{signal}:{strategy}"

    if not report:
        return MemoryWriteDecision(
            should_write=False,
            memory_type="skip",
            salience=0.0,
            confidence=confidence,
            reason="无报告，跳过 episodic 写入",
            dedup_key=dedup_key,
        )

    for chunk in recent_episodic[:3]:
        prev_sig, prev_strat, _ = _parse_signal_from_chunk(chunk)
        if prev_sig == signal and prev_strat == strategy:
            return MemoryWriteDecision(
                should_write=False,
                memory_type="skip",
                salience=0.2,
                confidence=confidence,
                reason=f"与近期 episodic 重复 ({dedup_key})",
                dedup_key=dedup_key,
            )

    salience = 0.7
    if risk_verdict == "reject":
        salience = 0.3
    elif confidence >= 70:
        salience = 0.85
    elif confidence < 40:
        salience = 0.45

    write_semantic = confidence >= 40 and bool((final_state or {}).get("risk_flags"))

    return MemoryWriteDecision(
        should_write=True,
        memory_type="episodic",
        salience=salience,
        confidence=confidence,
        reason="通过写入决策",
        dedup_key=dedup_key,
        write_semantic=write_semantic,
    )


def detect_conflicts(
    symbol: str,
    *,
    new_record: MemoryRecord,
    existing_meta: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """信号冲突时标记 contradicted / unverified。"""
    updated = [dict(r) for r in existing_meta]
    opposing = {"buy": "sell", "sell": "buy"}
    new_sig = new_record.signal_type.lower()

    for rec in updated:
        if rec.get("memory_type") != "episodic":
            continue
        old_sig = str(rec.get("signal_type", "")).lower()
        if opposing.get(new_sig) == old_sig or opposing.get(old_sig) == new_sig:
            rec["validation_status"] = "contradicted"
            new_record.validation_status = "unverified"
            new_record.supersedes.append(str(rec.get("memory_id", "")))

    return updated


def _expires_at_for_salience(salience: float) -> str | None:
    if salience >= 0.5:
        return None
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=LOW_SALIENCE_TTL_DAYS)
    return exp.strftime("%Y-%m-%d %H:%M UTC")


def consolidate_episodic_to_semantic(
    symbol: str,
    episodic_chunks: list[EvidenceChunk],
) -> list[dict[str, Any]]:
    """近 N 条 episodic 聚合为 semantic 摘要事实。"""
    episodic = [c for c in episodic_chunks if is_episodic_chunk(c)]
    if len(episodic) < 2:
        return load_semantic_facts(symbol)

    signals: list[str] = []
    strategies: list[str] = []
    flags: set[str] = set()
    for c in episodic[:5]:
        sig, strat, _ = _parse_signal_from_chunk(c)
        signals.append(sig)
        strategies.append(strat)
        for part in c.text.split("Risk flags from evidence:"):
            if len(part) > 1:
                tail = part.split("\n", 1)[0]
                for f in tail.replace("none", "").split(","):
                    f = f.strip()
                    if f:
                        flags.add(f)

    from collections import Counter

    top_sig = Counter(signals).most_common(1)[0][0] if signals else "unknown"
    top_strat = Counter(strategies).most_common(1)[0][0] if strategies else "unknown"
    flag_txt = ", ".join(sorted(flags)) if flags else "none"
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sym = symbol.upper()

    summary = (
        f"Semantic consolidation for {sym} ({len(episodic)} recent sessions): "
        f"dominant signal={top_sig}, strategy={top_strat}, "
        f"common risk_flags={flag_txt}."
    )
    fact = {
        "fact_id": f"{sym}_semantic_consolidated_{len(episodic)}",
        "title": f"{sym} episodic consolidation",
        "text": summary,
        "category": "consolidation",
        "source": "memory_lifecycle",
        "created_at": ts,
        "validation_status": "verified",
    }
    existing = load_semantic_facts(symbol)
    merged = merge_facts(existing, [fact])
    save_semantic_facts(symbol, merged)
    return merged


def memory_score_multiplier(doc_id: str, meta_records: list[dict[str, Any]]) -> float:
    """检索时对 contradicted / 过期记忆降权。"""
    for rec in meta_records:
        if rec.get("doc_id") != doc_id:
            continue
        status = rec.get("validation_status", "unverified")
        if status == "contradicted":
            return 0.5
        if status == "verified":
            return 1.1
        expires = rec.get("expires_at")
        if expires:
            try:
                exp = dt.datetime.strptime(expires[:16], "%Y-%m-%d %H:%M")
                exp = exp.replace(tzinfo=dt.timezone.utc)
                if dt.datetime.now(dt.timezone.utc) > exp:
                    return 0.0
            except ValueError:
                pass
    return 1.0


def is_memory_expired(doc_id: str, meta_records: list[dict[str, Any]]) -> bool:
    return memory_score_multiplier(doc_id, meta_records) == 0.0


def ingest_with_lifecycle(
    *,
    symbol: str,
    case_id: str,
    task: str,
    decision: dict[str, Any],
    risk_verdict: str | None,
    risk_reason: str | None,
    report: str | None,
    final_state: dict[str, Any] | None,
    recent_episodic: list[EvidenceChunk],
    existing_chunks: list[EvidenceChunk],
    merge_fn,
    persist_fn,
    semantic_ingest_fn,
    reindex_fn,
) -> EvidenceChunk | None:
    """
    带生命周期的 episodic 写入（由 EvidenceRetriever 注入依赖）。
    merge_fn(existing, [chunk]) -> merged
    persist_fn() -> None
    semantic_ingest_fn(symbol, report, decision, case_id) -> facts
    reindex_fn(symbol) -> None
    """
    write_dec = decide_memory_write(
        symbol,
        case_id=case_id,
        decision=decision,
        risk_verdict=risk_verdict,
        report=report,
        final_state=final_state,
        recent_episodic=recent_episodic,
    )
    if not write_dec.should_write:
        return None

    chunk = build_episodic_chunk(
        symbol,
        case_id=case_id,
        task=task,
        decision=decision,
        risk_verdict=risk_verdict,
        risk_reason=risk_reason,
        report=report,
        final_state=final_state,
    )

    signal = str(decision.get("signal_type", "unknown")).lower()
    strategy = str((final_state or {}).get("recommended_strategy", "unknown")).lower()
    try:
        confidence = float(decision.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    ts = chunk.published_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    record = MemoryRecord(
        memory_id=f"{symbol.upper()}_mem_{case_id}",
        doc_id=chunk.doc_id,
        memory_type="episodic",
        content=chunk.text[:500],
        source_run_id=case_id,
        signal_type=signal,
        strategy=strategy,
        confidence=confidence,
        salience=write_dec.salience,
        created_at=ts,
        validation_status="verified" if write_dec.salience >= 0.7 else "unverified",
        expires_at=_expires_at_for_salience(write_dec.salience),
    )

    meta = load_memory_meta(symbol)
    meta = detect_conflicts(symbol, new_record=record, existing_meta=meta)
    meta.append(record.to_dict())
    save_memory_meta(symbol, meta)

    merged = merge_fn(existing_chunks, [chunk])
    persist_fn(merged)

    if write_dec.write_semantic:
        try:
            semantic_ingest_fn(symbol, report, decision, case_id)
        except Exception:
            pass

    try:
        consolidate_episodic_to_semantic(symbol, merged)
        reindex_fn(symbol)
    except Exception:
        pass

    return chunk
