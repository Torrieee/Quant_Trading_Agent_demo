"""
Quant Trading Agent Demo

这个脚本展示了量化交易 Agent 的核心功能：
1. 使用 TradingAgent 类运行完整的交易流程
2. 自动调参功能
3. 结果可视化
"""

import datetime as dt
import matplotlib.pyplot as plt

from quant_agent import TradingAgent, AgentConfig, BacktestConfig, DataConfig, StrategyConfig
from quant_agent.optimizer import grid_search_on_strategy


def demo_single_strategy():
    """Demo 1: 运行单个策略的回测"""
    print("=" * 60)
    print("Demo 1: 单策略回测")
    print("=" * 60)
    
    # 配置 Agent
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2024, 1, 1),
    )
    
    strategy_cfg = StrategyConfig(
        name="mean_reversion",
        mr_window=20,
        mr_threshold=1.0,
    )
    
    backtest_cfg = BacktestConfig(
        initial_cash=100000,
        max_position=1.0,
        fee_rate=0.0005,
    )
    
    agent_cfg = AgentConfig(
        data=data_cfg,
        strategy=strategy_cfg,
        backtest=backtest_cfg,
    )
    
    # 创建并运行 Agent
    agent = TradingAgent(agent_cfg)
    result = agent.run()
    
    # 显示结果
    print("\n回测结果:")
    print("-" * 60)
    for key, value in result.backtest_result.stats.items():
        print(f"{key:>20}: {value:.4f}")
    
    # 绘制净值曲线
    df = result.backtest_result.data
    equity_col = result.backtest_result.equity_curve_col
    
    plt.figure(figsize=(12, 5))
    plt.plot(df.index, df[equity_col], label="Equity Curve", linewidth=2)
    plt.title(f"Equity Curve - {data_cfg.symbol} - {strategy_cfg.name}", fontsize=14)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Equity ($)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig("demo_equity_curve.png", dpi=150, bbox_inches="tight")
    print("\n净值曲线已保存为: demo_equity_curve.png")
    
    return result


def demo_auto_tuning():
    """Demo 2: 自动调参"""
    print("\n" + "=" * 60)
    print("Demo 2: 自动参数优化（网格搜索）")
    print("=" * 60)
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2024, 1, 1),
    )
    
    backtest_cfg = BacktestConfig(
        initial_cash=100000,
        max_position=1.0,
        fee_rate=0.0005,
    )
    
    # 定义参数网格
    param_grid = {
        "mr_window": [10, 20, 30],
        "mr_threshold": [0.8, 1.0, 1.2],
    }
    
    print(f"\n搜索空间: {len(param_grid['mr_window']) * len(param_grid['mr_threshold'])} 个参数组合")
    print("正在搜索最优参数...")
    
    # 运行网格搜索
    tuning_result = grid_search_on_strategy(
        data_cfg=data_cfg,
        base_bt_cfg=backtest_cfg,
        strategy_name="mean_reversion",
        param_grid=param_grid,
        metric="sharpe",
    )
    
    # 显示结果
    print("\n最优参数组合:")
    print("-" * 60)
    best_cfg = tuning_result.best_config
    print(f"策略: {best_cfg.strategy.name}")
    print(f"mr_window: {best_cfg.strategy.mr_window}")
    print(f"mr_threshold: {best_cfg.strategy.mr_threshold}")
    
    print("\n最优参数的回测结果:")
    print("-" * 60)
    for key, value in tuning_result.best_run.backtest_result.stats.items():
        print(f"{key:>20}: {value:.4f}")
    
    print("\nTop 5 参数组合:")
    print("-" * 60)
    print(tuning_result.summary.head(5).to_string(index=False))
    
    return tuning_result


def demo_compare_strategies():
    """Demo 3: 对比不同策略"""
    print("\n" + "=" * 60)
    print("Demo 3: 策略对比")
    print("=" * 60)
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2024, 1, 1),
    )
    
    backtest_cfg = BacktestConfig(
        initial_cash=100000,
        max_position=1.0,
        fee_rate=0.0005,
    )
    
    strategies = [
        StrategyConfig(name="mean_reversion", mr_window=20, mr_threshold=1.0),
        StrategyConfig(name="momentum", mom_short_window=20, mom_long_window=60),
    ]
    
    results = {}
    
    for strat_cfg in strategies:
        agent_cfg = AgentConfig(
            data=data_cfg,
            strategy=strat_cfg,
            backtest=backtest_cfg,
        )
        
        agent = TradingAgent(agent_cfg)
        result = agent.run()
        results[strat_cfg.name] = result
    
    # 对比结果
    print("\n策略对比:")
    print("-" * 60)
    print(f"{'指标':<20} {'均值回归':>15} {'动量策略':>15}")
    print("-" * 60)
    
    metrics = ["total_return", "annual_return", "sharpe", "max_drawdown"]
    for metric in metrics:
        mr_val = results["mean_reversion"].backtest_result.stats.get(metric, 0)
        mom_val = results["momentum"].backtest_result.stats.get(metric, 0)
        print(f"{metric:<20} {mr_val:>15.4f} {mom_val:>15.4f}")
    
    # 绘制对比图
    plt.figure(figsize=(14, 6))
    
    for name, result in results.items():
        df = result.backtest_result.data
        equity_col = result.backtest_result.equity_curve_col
        plt.plot(df.index, df[equity_col], label=name, linewidth=2)
    
    plt.title("Strategy Comparison - AAPL", fontsize=14)
    plt.xlabel("Date", fontsize=12)
    plt.ylabel("Equity ($)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig("demo_strategy_comparison.png", dpi=150, bbox_inches="tight")
    print("\n策略对比图已保存为: demo_strategy_comparison.png")
    
    return results


def main():
    """运行所有 demo"""
    print("\n" + "=" * 60)
    print("Quant Trading Agent - Demo")
    print("=" * 60)
    print("\n本 demo 将展示以下功能：")
    print("1. 单策略回测")
    print("2. 自动参数优化")
    print("3. 策略对比")
    print("\n注意：首次运行需要下载数据，可能需要一些时间...")
    print("=" * 60)
    
    try:
        # Demo 1: 单策略
        result1 = demo_single_strategy()
        
        # Demo 2: 自动调参（可选，因为比较耗时）
        print("\n是否运行自动调参 demo？（需要较长时间，输入 y/n）")
        choice = input().strip().lower()
        if choice == 'y':
            result2 = demo_auto_tuning()
        
        # Demo 3: 策略对比
        result3 = demo_compare_strategies()
        
        print("\n" + "=" * 60)
        print("所有 Demo 完成！")
        print("=" * 60)
        print("\n生成的文件：")
        print("- demo_equity_curve.png: 单策略净值曲线")
        print("- demo_strategy_comparison.png: 策略对比图")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


