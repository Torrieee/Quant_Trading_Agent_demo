"""模拟盘执行层：订单、持仓、持久化。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _portfolio_path() -> Path:
    return Path(os.environ.get("PAPER_PORTFOLIO_PATH", "data_cache/paper/portfolio.json"))


def load_portfolio() -> dict[str, Any]:
    path = _portfolio_path()
    if not path.is_file():
        return {
            "cash": float(os.environ.get("PAPER_INITIAL_CASH", "100000")),
            "positions": {},
            "orders": [],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"cash": 100_000.0, "positions": {}, "orders": []}


def save_portfolio(data: dict[str, Any]) -> None:
    path = _portfolio_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def submit_paper_order(
    symbol: str,
    side: str,
    quantity: float,
    price: float | None = None,
    *,
    case_id: str | None = None,
) -> dict[str, Any]:
    """
    模拟下单；price 为空时视为市价（需外部传入现价）。
    side: buy | sell
    """
    sym = symbol.upper()
    side = side.lower()
    if side not in ("buy", "sell"):
        return {"error": "side must be buy or sell"}
    if quantity <= 0:
        return {"error": "quantity must be positive"}

    pf = load_portfolio()
    cash = float(pf.get("cash", 0))
    positions: dict[str, Any] = dict(pf.get("positions") or {})
    pos = positions.get(sym, {"qty": 0.0, "avg_price": 0.0})
    qty = float(pos.get("qty", 0))
    avg = float(pos.get("avg_price", 0))

    if price is None or price <= 0:
        return {"error": "price required for paper order"}

    notional = quantity * price
    order = {
        "symbol": sym,
        "side": side,
        "quantity": quantity,
        "price": price,
        "notional": round(notional, 2),
        "case_id": case_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    if side == "buy":
        if notional > cash:
            return {"error": "insufficient cash", "cash": cash, "required": notional}
        cash -= notional
        new_qty = qty + quantity
        avg = ((avg * qty) + notional) / new_qty if new_qty else price
        pos = {"qty": new_qty, "avg_price": round(avg, 4)}
    else:
        if quantity > qty:
            return {"error": "insufficient position", "held": qty}
        cash += notional
        new_qty = qty - quantity
        pos = {"qty": new_qty, "avg_price": avg if new_qty > 0 else 0.0}

    positions[sym] = pos
    orders = list(pf.get("orders") or [])
    orders.append(order)
    pf["cash"] = round(cash, 2)
    pf["positions"] = positions
    pf["orders"] = orders[-200:]
    save_portfolio(pf)
    return {"status": "filled", "order": order, "portfolio": {"cash": pf["cash"], "positions": positions}}
