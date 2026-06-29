"""信号聚合：多智能体加权投票生成初步决策。"""

from __future__ import annotations

from typing import Any

from .base import AgentSignal
from .state import DEFAULT_AGENT_WEIGHTS


def aggregate_signals(
    signals: dict[str, AgentSignal],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """对多个智能体信号做加权投票，输出初步投资决策。"""
    if not signals:
        return {
            "signal_type": "hold",
            "confidence": 0,
            "reasoning": "没有可用的分析信号",
            "scores": {"buy": 0, "sell": 0, "hold": 0},
        }

    weights = weights or DEFAULT_AGENT_WEIGHTS
    buy_score = 0.0
    sell_score = 0.0
    hold_score = 0.0
    total_weight = 0.0
    details: list[dict[str, Any]] = []

    for agent_name, signal in signals.items():
        weight = weights.get(agent_name, 0.33)
        confidence = signal.confidence / 100.0
        weighted = weight * confidence
        total_weight += weight

        if signal.signal_type == "buy":
            buy_score += weighted
        elif signal.signal_type == "sell":
            sell_score += weighted
        else:
            hold_score += weighted

        details.append(
            {
                "agent": agent_name,
                "signal": signal.signal_type,
                "confidence": signal.confidence,
                "weight": weight,
            }
        )

    if total_weight > 0:
        buy_score /= total_weight
        sell_score /= total_weight
        hold_score /= total_weight

    scores = {"buy": buy_score, "sell": sell_score, "hold": hold_score}
    final_signal = max(scores, key=scores.get)
    final_confidence = scores[final_signal] * 100

    reasoning_lines = [
        f"初步综合决策: {final_signal.upper()}（置信度 {final_confidence:.1f}%）",
        "",
        "各智能体意见:",
    ]
    for item in details:
        reasoning_lines.append(
            f"- {item['agent']}（权重 {item['weight']*100:.0f}%）: "
            f"{item['signal'].upper()}（置信度 {item['confidence']}%）"
        )

    return {
        "signal_type": final_signal,
        "confidence": round(final_confidence, 2),
        "reasoning": "\n".join(reasoning_lines),
        "scores": {k: round(v * 100, 2) for k, v in scores.items()},
        "signal_details": details,
    }
