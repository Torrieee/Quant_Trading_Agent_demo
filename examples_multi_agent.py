"""示例：QuantEngine 多智能体分析（需 DEEPSEEK_API_KEY）。"""

import sys

from quant_agent import QuantEngine
from quant_agent.agents.llm import DeepSeekConfigError, require_deepseek_chat_model


def main() -> None:
    try:
        model = require_deepseek_chat_model()
    except DeepSeekConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)

    result = QuantEngine(model=model).analyze(
        "AAPL",
        task="震荡市环境下给出策略与仓位建议",
        gate={
            "risk_method": "kelly",
            "win_rate": 0.55,
            "avg_win": 0.02,
            "avg_loss": 0.01,
        },
    )

    print("success:", result.success)
    print("decision:", result.decision.get("signal_type"), result.decision.get("confidence"))
    print("agents:", result.agents_visited)
    print("risk:", result.risk_verdict)
    print("\n--- report ---\n")
    print(result.report or "")


if __name__ == "__main__":
    main()
