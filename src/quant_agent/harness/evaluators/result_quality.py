"""Result completeness checks — not profitability."""

from __future__ import annotations

import math
from typing import Any


def validate_result_quality(
    stats: dict[str, Any],
    *,
    min_days: int,
    required_stats: list[str],
) -> dict[str, Any]:
    """Structural result quality gate (no Sharpe thresholds)."""
    failures: list[str] = []

    for key in required_stats:
        if key not in stats:
            failures.append(f"result_schema_valid: missing key '{key}'")

    for key in required_stats:
        if key not in stats:
            continue
        value = stats[key]
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            failures.append(f"no_nan_metrics: '{key}' is {value}")

    if "num_days" in stats and stats["num_days"] < min_days:
        failures.append(
            f"num_days_valid: {stats['num_days']} < required {min_days}"
        )

    for trade_key in ("num_trades", "win_rate"):
        if trade_key in required_stats and trade_key not in stats:
            failures.append(f"trades_field_present: missing '{trade_key}'")

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "checks": {
            "result_schema_valid": not any("result_schema_valid" in f for f in failures),
            "no_nan_metrics": not any("no_nan_metrics" in f for f in failures),
            "num_days_valid": not any("num_days_valid" in f for f in failures),
            "trades_field_present": not any("trades_field_present" in f for f in failures),
        },
    }
