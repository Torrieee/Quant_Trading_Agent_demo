"""评测用假 LLM：确定性模拟 Research / Risk / Reporter ReAct 行为。"""

from __future__ import annotations

from langchain_core.messages import AIMessage


class RoleAwareFakeModel:
    """默认假模型：Research 调策略推荐，Risk 调 Kelly 仓位，Reporter 输出 Markdown。"""

    def __init__(self, *, market_state: str = "ranging") -> None:
        self._market_state = market_state
        self._research_calls = 0
        self._risk_calls = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        system = ""
        for m in messages:
            if getattr(m, "type", None) == "system":
                system = m.content
                break

        # 研究 prompt 中含「Risk 智能体」字样，须用更精确的前缀匹配
        if "你是量化研究智能体" in system:
            self._research_calls += 1
            if self._research_calls > 1:
                return AIMessage(content="Research complete.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_strategy_recommendation",
                        "args": {"market_state": self._market_state},
                        "id": "research-1",
                    }
                ],
            )
        if "你是 Risk 智能体" in system:
            self._risk_calls += 1
            if self._risk_calls > 1:
                return AIMessage(content="Risk complete.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculate_position_size",
                        "args": {
                            "method": "kelly",
                            "win_rate": 0.55,
                            "avg_win": 0.02,
                            "avg_loss": 0.01,
                        },
                        "id": "risk-1",
                    }
                ],
            )
        if "Reporter" in system:
            return AIMessage(
                content=(
                    "# Report\n\n"
                    f"Summary: {self._market_state} market → mean_reversion strategy.\n"
                )
            )
        return AIMessage(content="done")


class HighPositionFakeModel(RoleAwareFakeModel):
    """Risk 返回超大仓位，用于触发规则 reject。"""

    def invoke(self, messages):
        system = ""
        for m in messages:
            if getattr(m, "type", None) == "system":
                system = m.content
                break
        if "你是 Risk 智能体" in system:
            self._risk_calls += 1
            if self._risk_calls > 1:
                return AIMessage(content="Risk complete.")
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculate_position_size",
                        "args": {
                            "method": "volatility_targeting",
                            "volatility": 0.05,
                        },
                        "id": "risk-high",
                    }
                ],
            )
        return super().invoke(messages)


def resolve_fake_model(name: str | None = None) -> RoleAwareFakeModel:
    """按 case 配置选择假模型。"""
    key = (name or "default").lower()
    if key in ("high_position", "oversize", "reject"):
        return HighPositionFakeModel()
    if key.startswith("trend"):
        return RoleAwareFakeModel(market_state="trending_up")
    return RoleAwareFakeModel()
