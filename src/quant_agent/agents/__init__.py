"""多智能体协调与工作流节点。"""

from .base import AgentSignal, BaseAgent
from .coordinator import AgentCoordinator, build_coordinator_graph, run_workflow
from .fundamental import FundamentalAgent
from .research_analyst import ResearchAnalystAgent
from .sentiment import SentimentAgent
from .signal_aggregate import aggregate_signals
from .state import WorkflowState, initial_state

__all__ = [
    "AgentSignal",
    "BaseAgent",
    "FundamentalAgent",
    "SentimentAgent",
    "ResearchAnalystAgent",
    "AgentCoordinator",
    "aggregate_signals",
    "build_coordinator_graph",
    "run_workflow",
    "WorkflowState",
    "initial_state",
]
