"""披露证据 → 投资决策修正（document_signal）。"""

from __future__ import annotations

from typing import Any

# 风险标记对信号的影响
_FLAG_IMPACT: dict[str, dict[str, float]] = {
    "going_concern": {"buy": -40, "hold": -10, "sell": +15, "cap_confidence": 35},
    "bankruptcy": {"buy": -50, "hold": -15, "sell": +20, "cap_confidence": 30},
    "material_weakness": {"buy": -15, "hold": -5, "sell": +5, "cap_confidence": 70},
    "regulatory": {"buy": -12, "hold": -5, "sell": +8, "cap_confidence": 75},
    "supply_chain": {"buy": -8, "hold": -3, "sell": +5, "cap_confidence": 85},
}


def revise_decision_from_evidence(
    preliminary: dict[str, Any],
    *,
    risk_flags: list[str],
    event_severity: str = "low",
) -> dict[str, Any]:
    """
    基于 document_flags / risk_flags 修正初步决策。
    返回含 document_signal 字段的决策 dict。
    """
    if not preliminary:
        preliminary = {
            "signal_type": "hold",
            "confidence": 0,
            "reasoning": "",
            "scores": {"buy": 0, "sell": 0, "hold": 0},
        }

    scores = dict(preliminary.get("scores") or {"buy": 0, "sell": 0, "hold": 0})
    for k in ("buy", "sell", "hold"):
        scores.setdefault(k, 0.0)

    adjustments: list[str] = []
    cap = 100.0
    for flag in risk_flags:
        impact = _FLAG_IMPACT.get(flag)
        if not impact:
            continue
        for sig in ("buy", "sell", "hold"):
            scores[sig] = scores.get(sig, 0) + impact.get(sig, 0)
        if "cap_confidence" in impact:
            cap = min(cap, impact["cap_confidence"])
        adjustments.append(flag)

    if event_severity == "high" and not adjustments:
        cap = min(cap, 40.0)
        adjustments.append("high_severity_event")

    for k in scores:
        scores[k] = max(0.0, float(scores[k]))

    total = sum(scores.values()) or 1.0
    norm = {k: round(v / total * 100, 2) for k, v in scores.items()}
    final_signal = max(norm, key=norm.get)
    confidence = min(cap, norm[final_signal])

    orig_signal = preliminary.get("signal_type", "hold")
    orig_conf = preliminary.get("confidence", 0)

    reasoning = preliminary.get("reasoning", "")
    if adjustments:
        reasoning += (
            "\n\n[Document Signal] 披露风险修正: "
            + ", ".join(adjustments)
            + f"。信号 {orig_signal.upper()}({orig_conf}%) → "
            + f"{final_signal.upper()}({confidence:.1f}%)."
        )

    return {
        **preliminary,
        "signal_type": final_signal,
        "confidence": round(confidence, 2),
        "scores": norm,
        "reasoning": reasoning.strip(),
        "document_signal": {
            "applied": bool(adjustments),
            "risk_flags": list(risk_flags),
            "event_severity": event_severity,
            "adjustments": adjustments,
            "original_signal": orig_signal,
            "original_confidence": orig_conf,
        },
    }
