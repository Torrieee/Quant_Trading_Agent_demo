"""投资智能体基类与信号模型。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentSignal(BaseModel):
    """单个分析智能体输出的交易信号。"""

    agent_name: str
    signal_type: str  # buy | sell | hold
    confidence: float  # 0-100
    reasoning: str
    target_price: float | None = None
    stop_loss: float | None = None
    time_horizon: str = "medium"  # short | medium | long
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """分析类智能体抽象基类。"""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"quant_agent.agents.{name}")

    @abstractmethod
    def analyze(self, symbol: str, data: dict[str, Any]) -> AgentSignal:
        """根据输入数据生成交易信号。"""

    def validate_data(self, data: dict[str, Any], required_keys: list[str]) -> bool:
        """校验分析所需字段是否齐全。"""
        for key in required_keys:
            if key not in data or data[key] is None:
                self.logger.warning("缺少必要数据: %s", key)
                return False
        return True
