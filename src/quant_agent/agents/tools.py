"""按角色划分的工具规范与执行。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..runtime.tool_adapter import HarnessToolAdapter
from .state import RESEARCH_TOOL_NAMES, RISK_TOOL_NAMES

RecordFn = Callable[[str, dict[str, Any], dict[str, Any], float, str], None]


def get_openai_tool_specs_for_role(
    adapter: HarnessToolAdapter,
    role: str,
) -> list[dict[str, Any]]:
    if role == "research":
        allowed = RESEARCH_TOOL_NAMES
    elif role == "risk":
        allowed = RISK_TOOL_NAMES
    else:
        return []

    specs: list[dict[str, Any]] = []
    for spec in adapter.caller.get_available_functions():
        if spec["name"] not in allowed:
            continue
        specs.append({"type": "function", "function": spec})
    return specs


def execute_tool_step(
    adapter: HarnessToolAdapter,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    on_invoke: RecordFn | None = None,
) -> tuple[dict[str, Any], bool, float, str | None]:
    from ..runtime.trace import ToolCallRequest

    response = adapter.invoke_with_policy(ToolCallRequest(name=tool_name, arguments=arguments))
    latency_ms = response.latency_ms
    data = response.data if isinstance(response.data, dict) else {"result": response.data}
    if response.retry_count > 0:
        data = {**data, "retry_count": response.retry_count}
    if response.output_truncated:
        data = {**data, "output_truncated": True}
    if on_invoke is not None:
        on_invoke(
            tool_name,
            arguments,
            data,
            latency_ms,
            "ok" if response.ok else "failed",
        )
    return data, response.ok, latency_ms, response.error_code


def merge_observation(state: dict[str, Any], observation: dict[str, Any]) -> None:
    for key, value in observation.items():
        if key == "error":
            continue
        if key == "retrieved_documents" and isinstance(value, list):
            existing = state.get("retrieved_documents")
            if not isinstance(existing, list):
                state["retrieved_documents"] = list(value)
            else:
                seen = {d.get("doc_id") for d in existing if isinstance(d, dict)}
                for doc in value:
                    if isinstance(doc, dict) and doc.get("doc_id") not in seen:
                        existing.append(doc)
                        seen.add(doc.get("doc_id"))
            continue
        state[key] = value


def enrich_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    quant_state: dict[str, Any],
    *,
    symbol: str | None = None,
) -> dict[str, Any]:
    """从 quant_state 为工具调用补全 symbol / risk_flags 等。"""
    args = dict(arguments)
    sym = args.get("symbol") or quant_state.get("symbol") or symbol
    if sym and tool_name in ("get_strategy_recommendation", "search_evidence", "get_market_data", "analyze_market_state", "run_backtest"):
        args.setdefault("symbol", sym)
    if tool_name == "get_strategy_recommendation":
        if not args.get("risk_flags") and quant_state.get("risk_flags"):
            args["risk_flags"] = quant_state["risk_flags"]
        if args.get("volatility") is None and quant_state.get("volatility") is not None:
            args.setdefault("volatility", quant_state.get("volatility"))
        if args.get("trend_strength") is None and quant_state.get("trend_strength") is not None:
            args.setdefault("trend_strength", quant_state.get("trend_strength"))
    return args
