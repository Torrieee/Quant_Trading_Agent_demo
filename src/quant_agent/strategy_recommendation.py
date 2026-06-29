"""策略推荐：基于市场状态指标对候选策略打分（替代简单查表）。"""

from __future__ import annotations

from typing import Any

from .market_state import MarketRegime, MarketState, get_optimal_strategy_for_regime

CANDIDATE_STRATEGIES = ("momentum", "mean_reversion")

# 各 regime 下的典型指标（仅当调用方未提供真实 volatility/trend 时使用）
_REGIME_DEFAULTS: dict[str, dict[str, float | bool]] = {
    "trending_up": {
        "volatility": 0.18,
        "trend_strength": 0.75,
        "is_bullish": True,
        "is_bearish": False,
    },
    "trending_down": {
        "volatility": 0.22,
        "trend_strength": 0.72,
        "is_bullish": False,
        "is_bearish": True,
    },
    "ranging": {
        "volatility": 0.16,
        "trend_strength": 0.25,
        "is_bullish": False,
        "is_bearish": False,
    },
    "high_volatility": {
        "volatility": 0.38,
        "trend_strength": 0.35,
        "is_bullish": False,
        "is_bearish": False,
    },
    "low_volatility": {
        "volatility": 0.12,
        "trend_strength": 0.40,
        "is_bullish": True,
        "is_bearish": False,
    },
}


def _regime_from_string(market_state: str) -> MarketRegime | None:
    mapping = {
        "trending_up": MarketRegime.TRENDING_UP,
        "trending_down": MarketRegime.TRENDING_DOWN,
        "ranging": MarketRegime.RANGING,
        "high_volatility": MarketRegime.HIGH_VOLATILITY,
        "low_volatility": MarketRegime.LOW_VOLATILITY,
    }
    return mapping.get(market_state)


def _build_market_state(
    regime: MarketRegime,
    *,
    volatility: float | None,
    trend_strength: float | None,
    is_bullish: bool | None,
    is_bearish: bool | None,
) -> MarketState:
    defaults = _REGIME_DEFAULTS.get(regime.value, _REGIME_DEFAULTS["ranging"])
    vol = volatility if volatility is not None else float(defaults["volatility"])  # type: ignore[arg-type]
    trend = trend_strength if trend_strength is not None else float(defaults["trend_strength"])  # type: ignore[arg-type]
    bullish = is_bullish if is_bullish is not None else bool(defaults["is_bullish"])
    bearish = is_bearish if is_bearish is not None else bool(defaults["is_bearish"])
    return MarketState(
        regime=regime,
        volatility=vol,
        trend_strength=trend,
        adx=trend * 25.0,
        atr=vol * 10.0,
        bollinger_width=vol * 0.5,
        is_bullish=bullish,
        is_bearish=bearish,
    )


def _score_strategy(strategy: str, state: MarketState, risk_flags: list[str]) -> float:
    """对单个策略计算 0–1 得分。"""
    regime = state.regime
    vol = state.volatility
    trend = state.trend_strength
    score = 0.5

    if strategy == "momentum":
        if regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            score += 0.25 + 0.15 * trend
        elif regime == MarketRegime.LOW_VOLATILITY:
            score += 0.15
        elif regime == MarketRegime.RANGING:
            score -= 0.15
        elif regime == MarketRegime.HIGH_VOLATILITY:
            score -= 0.20
        if vol > 0.32:
            score -= 0.10
    else:  # mean_reversion
        if regime == MarketRegime.RANGING:
            score += 0.25
        elif regime == MarketRegime.HIGH_VOLATILITY:
            score += 0.15
        elif regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            score -= 0.10 - 0.05 * (1 - trend)
        if vol > 0.30:
            score += 0.08

    for flag in risk_flags:
        flag_lower = flag.lower()
        if flag_lower in ("going_concern", "bankruptcy", "material_weakness", "regulatory"):
            if strategy == "momentum":
                score -= 0.20
            else:
                score += 0.05

    return max(0.0, min(1.0, score))


def recommend_strategy(
    *,
    symbol: str,
    market_state: str,
    volatility: float | None = None,
    trend_strength: float | None = None,
    is_bullish: bool | None = None,
    is_bearish: bool | None = None,
    risk_flags: list[str] | None = None,
) -> dict[str, Any]:
    """
    根据市场状态与可选真实指标，对 momentum / mean_reversion 打分并返回推荐。
    """
    regime = _regime_from_string(market_state)
    if regime is None:
        return {"error": f"Unknown market state: {market_state}"}

    flags = list(risk_flags or [])
    ms = _build_market_state(
        regime,
        volatility=volatility,
        trend_strength=trend_strength,
        is_bullish=is_bullish,
        is_bearish=is_bearish,
    )

    scores = {s: _score_strategy(s, ms, flags) for s in CANDIDATE_STRATEGIES}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    primary_score = ranked[0][1]
    baseline = get_optimal_strategy_for_regime(ms)

    # 若打分与 regime 查表不一致，保留打分结果并在 reason 中说明
    alternatives = [
        {
            "strategy": name,
            "score": round(sc, 3),
            "reason": _alternative_reason(name, sc, primary, ms),
        }
        for name, sc in ranked[1:]
    ]

    confidence = round(min(0.95, 0.45 + primary_score * 0.5), 3)
    if flags:
        confidence = round(min(confidence, 0.65), 3)

    inputs_used = {
        "volatility": round(ms.volatility, 4),
        "trend_strength": round(ms.trend_strength, 4),
        "is_bullish": ms.is_bullish,
        "is_bearish": ms.is_bearish,
        "source": "arguments" if volatility is not None else "regime_defaults",
        "regime_baseline_strategy": baseline,
    }

    reason = (
        f"标的 {symbol} 市场状态 {market_state}（波动率 {ms.volatility:.2%}，"
        f"趋势强度 {ms.trend_strength:.2f}）。"
        f"推荐 {primary}（得分 {primary_score:.2f}，置信度 {confidence:.2f}）。"
    )
    if primary != baseline:
        reason += f" 与纯 regime 映射（{baseline}）不同，因波动/风险因子调整。"
    if flags:
        reason += f" 风险标记: {', '.join(flags)}。"

    return {
        "symbol": symbol,
        "market_state": market_state,
        "recommended_strategy": primary,
        "alternatives": alternatives,
        "confidence": confidence,
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "reason": reason,
        "inputs_used": inputs_used,
        "risk_flags": flags,
    }


def _alternative_reason(name: str, score: float, primary: str, state: MarketState) -> str:
    if name == primary:
        return "首选策略"
    if score >= 0.45:
        return f"可作为备选验证（{state.regime.value}）"
    return "得分偏低，不建议优先回测"
