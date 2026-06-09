"""
快速 Demo - 展示量化交易 Agent 的核心功能

运行方式：
    python quick_demo.py
"""

import datetime as dt

from quant_agent import TradingAgent, AgentConfig, BacktestConfig, DataConfig, StrategyConfig


def main():
    print("=" * 60)
    print("Quant Trading Agent - 快速演示")
    print("=" * 60)
    
    # 1. 配置 Agent
    print("\n[1/4] 配置 Agent...")
    # 提示：可以修改 symbol 使用其他股票
    # 美股: AAPL, MSFT, TSLA, GOOGL 等
    # A股: 600519.SS (贵州茅台), 000001.SZ (平安银行) 等
    # 港股: 0700.HK (腾讯), 0941.HK (中国移动) 等
    agent_cfg = AgentConfig(
        data=DataConfig(
            symbol="AAPL",  # 可以修改为其他股票代码
            start=dt.date(2020, 1, 1),  # 使用较短的时间范围，加快演示速度
            end=dt.date(2023, 1, 1),
        ),
        strategy=StrategyConfig(
            name="mean_reversion",
            mr_window=20,
            mr_threshold=1.0,
        ),
        backtest=BacktestConfig(
            initial_cash=100000,
            max_position=1.0,
            fee_rate=0.0005,
        ),
    )
    print("✓ 配置完成")
    
    # 2. 创建 Agent
    print("\n[2/4] 创建 TradingAgent...")
    agent = TradingAgent(agent_cfg)
    print("✓ Agent 创建完成")
    
    # 3. 运行 Agent（自动执行：感知 -> 决策 -> 执行 -> 评估）
    print("\n[3/4] 运行 Agent（感知-决策-执行-评估）...")
    result = agent.run()
    print("✓ Agent 运行完成")
    
    # 4. 显示结果
    print("\n[4/4] 回测结果:")
    print("-" * 60)
    stats = result.backtest_result.stats
    print(f"总收益率:     {stats.get('total_return', 0):>10.2%}")
    print(f"年化收益率:   {stats.get('annual_return', 0):>10.2%}")
    print(f"夏普比率:     {stats.get('sharpe', 0):>10.4f}")
    print(f"最大回撤:     {stats.get('max_drawdown', 0):>10.2%}")
    print(f"胜率:         {stats.get('win_rate', 0):>10.2%}")
    print("-" * 60)
    
    print("\n" + "=" * 60)
    print("Demo 完成！")
    print("=" * 60)
    print("\n提示：")
    print("- 运行完整 demo: python demo.py")
    print("- 运行自动调参: python -m scripts.tune_agent --symbol AAPL --strategy mean_reversion --start 2020-01-01 --end 2023-01-01")
    print("- 查看帮助: python -m scripts.run_agent --help")


if __name__ == "__main__":
    main()


