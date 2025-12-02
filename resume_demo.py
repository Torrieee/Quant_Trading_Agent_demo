"""
量化交易Agent - 简历展示Demo

展示项目的核心功能：
1. 传统策略回测（均值回归、动量）
2. 市场状态识别和动态策略选择
3. 智能仓位管理
4. 强化学习训练（可选）
5. 结果可视化和报告生成
"""

import datetime as dt
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from quant_agent import (
    AgentConfig,
    BacktestConfig,
    DataConfig,
    StrategyConfig,
    TradingAgent,
)
from quant_agent.market_state import (
    get_optimal_strategy_for_regime,
    identify_market_state,
)
from quant_agent.position_sizing import (
    calculate_trade_statistics,
    kelly_position_size,
    risk_parity_position_size,
)


def print_section(title: str):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_traditional_strategies():
    """Demo 1: 传统策略回测对比"""
    print_section("Demo 1: 传统策略回测对比")
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2025, 1, 1),
    )
    
    backtest_cfg = BacktestConfig(
        initial_cash=100000,
        max_position=1.0,
        fee_rate=0.0005,
    )
    
    strategies = [
        ("均值回归策略", StrategyConfig(name="mean_reversion", mr_window=20, mr_threshold=1.0)),
        ("动量策略", StrategyConfig(name="momentum", mom_short_window=20, mom_long_window=60)),
    ]
    
    results = {}
    equity_curves = {}
    
    for name, strat_cfg in strategies:
        print(f"\n运行 {name}...")
        agent_cfg = AgentConfig(
            data=data_cfg,
            strategy=strat_cfg,
            backtest=backtest_cfg,
        )
        
        agent = TradingAgent(agent_cfg)
        result = agent.run()
        
        results[name] = result.backtest_result.stats
        equity_curves[name] = result.backtest_result.data[
            result.backtest_result.equity_curve_col
        ]
    
    # 打印对比结果
    print("\n策略对比结果:")
    print("-" * 70)
    print(f"{'指标':<20} {'均值回归':>15} {'动量策略':>15}")
    print("-" * 70)
    
    metrics = ["total_return", "annual_return", "sharpe", "max_drawdown"]
    metric_names = {
        "total_return": "总收益率",
        "annual_return": "年化收益率",
        "sharpe": "夏普比率",
        "max_drawdown": "最大回撤",
    }
    
    for metric in metrics:
        mr_val = results["均值回归策略"].get(metric, 0)
        mom_val = results["动量策略"].get(metric, 0)
        name = metric_names.get(metric, metric)
        
        if metric in ["total_return", "annual_return", "max_drawdown"]:
            print(f"{name:<20} {mr_val:>15.2%} {mom_val:>15.2%}")
        else:
            print(f"{name:<20} {mr_val:>15.4f} {mom_val:>15.4f}")
    
    # 绘制净值曲线对比
    plt.figure(figsize=(14, 6))
    for name, equity in equity_curves.items():
        plt.plot(equity.index, equity.values, label=name, linewidth=2)
    
    plt.title("策略净值曲线对比 - AAPL (2018-2025)", fontsize=16, fontweight="bold")
    plt.xlabel("日期", fontsize=12)
    plt.ylabel("净值 ($)", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    os.makedirs("demo_output", exist_ok=True)
    plt.savefig("demo_output/strategy_comparison.png", dpi=150, bbox_inches="tight")
    print(f"\n✓ 净值曲线对比图已保存: demo_output/strategy_comparison.png")
    plt.close()
    
    return results, equity_curves


def demo_market_state_detection():
    """Demo 2: 市场状态识别和动态策略选择"""
    print_section("Demo 2: 市场状态识别和动态策略选择")
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2025, 1, 1),
    )
    
    # 获取数据并识别市场状态
    from quant_agent.data import download_ohlcv
    
    df = download_ohlcv(data_cfg)
    market_state = identify_market_state(df)
    
    print(f"\n市场状态分析:")
    print(f"  状态类型: {market_state.regime.value}")
    print(f"  年化波动率: {market_state.volatility:.2%}")
    print(f"  趋势强度: {market_state.trend_strength:.2f} (0-1)")
    print(f"  ADX指标: {market_state.adx:.2f}")
    print(f"  市场方向: {'看涨' if market_state.is_bullish else '看跌' if market_state.is_bearish else '中性'}")
    
    # 根据市场状态推荐策略
    recommended_strategy = get_optimal_strategy_for_regime(market_state)
    print(f"\n推荐策略: {recommended_strategy}")
    print(f"  理由: 当前市场为{market_state.regime.value}，适合使用{recommended_strategy}策略")
    
    # 使用推荐策略运行回测
    strategy_cfg = StrategyConfig(name=recommended_strategy)
    backtest_cfg = BacktestConfig(initial_cash=100000)
    agent_cfg = AgentConfig(
        data=data_cfg,
        strategy=strategy_cfg,
        backtest=backtest_cfg,
    )
    
    agent = TradingAgent(agent_cfg)
    result = agent.run()
    
    print(f"\n推荐策略回测结果:")
    print(f"  总收益率: {result.backtest_result.stats['total_return']:.2%}")
    print(f"  年化收益率: {result.backtest_result.stats['annual_return']:.2%}")
    print(f"  夏普比率: {result.backtest_result.stats['sharpe']:.4f}")
    print(f"  最大回撤: {result.backtest_result.stats['max_drawdown']:.2%}")
    
    return market_state, result


def demo_intelligent_position_sizing():
    """Demo 3: 智能仓位管理"""
    print_section("Demo 3: 智能仓位管理")
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2025, 1, 1),
    )
    
    strategy_cfg = StrategyConfig(name="mean_reversion")
    backtest_cfg = BacktestConfig(initial_cash=100000)
    agent_cfg = AgentConfig(
        data=data_cfg,
        strategy=strategy_cfg,
        backtest=backtest_cfg,
    )
    
    agent = TradingAgent(agent_cfg)
    result = agent.run()
    
    # 计算交易统计
    equity_curve = result.backtest_result.data[result.backtest_result.equity_curve_col]
    signals = result.strategy_result.data[result.strategy_result.signal_col]
    
    trade_stats = calculate_trade_statistics(equity_curve, signals)
    
    print(f"\n交易统计:")
    print(f"  交易次数: {trade_stats['num_trades']}")
    print(f"  胜率: {trade_stats['win_rate']:.2%}")
    print(f"  平均盈利: {trade_stats['avg_win']:.2%}")
    print(f"  平均亏损: {trade_stats['avg_loss']:.2%}")
    
    # 凯利公式
    if trade_stats['num_trades'] > 0:
        kelly_position = kelly_position_size(
            win_rate=trade_stats['win_rate'],
            avg_win=trade_stats['avg_win'],
            avg_loss=trade_stats['avg_loss'],
            kelly_fraction=0.25
        )
        print(f"\n凯利公式建议仓位: {kelly_position:.2%}")
        print(f"  (使用1/4凯利，更保守)")
    
    # 风险平价
    market_state = identify_market_state(result.strategy_result.data)
    risk_parity_position = risk_parity_position_size(
        volatility=market_state.volatility,
        target_volatility=0.15,
        max_position=1.0
    )
    print(f"风险平价建议仓位: {risk_parity_position:.2%}")
    print(f"  (目标波动率: 15%)")
    
    print(f"\n固定仓位（当前）: {backtest_cfg.max_position:.2%}")
    
    return trade_stats


def demo_parameter_optimization():
    """Demo 4: 自动参数优化"""
    print_section("Demo 4: 自动参数优化（网格搜索）")
    
    from quant_agent.optimizer import grid_search_on_strategy
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2018, 1, 1),
        end=dt.date(2023, 1, 1),
    )
    
    backtest_cfg = BacktestConfig(initial_cash=100000)
    
    # 定义参数网格
    param_grid = {
        "mr_window": [15, 20, 25],
        "mr_threshold": [0.8, 1.0, 1.2],
    }
    
    print(f"\n参数搜索空间: {len(param_grid['mr_window']) * len(param_grid['mr_threshold'])} 个组合")
    print("正在搜索最优参数...")
    
    tuning_result = grid_search_on_strategy(
        data_cfg=data_cfg,
        base_bt_cfg=backtest_cfg,
        strategy_name="mean_reversion",
        param_grid=param_grid,
        metric="sharpe",
    )
    
    print(f"\n最优参数组合:")
    best_cfg = tuning_result.best_config
    print(f"  mr_window: {best_cfg.strategy.mr_window}")
    print(f"  mr_threshold: {best_cfg.strategy.mr_threshold}")
    
    print(f"\n最优参数回测结果:")
    stats = tuning_result.best_run.backtest_result.stats
    print(f"  总收益率: {stats['total_return']:.2%}")
    print(f"  年化收益率: {stats['annual_return']:.2%}")
    print(f"  夏普比率: {stats['sharpe']:.4f}")
    print(f"  最大回撤: {stats['max_drawdown']:.2%}")
    
    print(f"\nTop 3 参数组合:")
    print(tuning_result.summary.head(3)[["mr_window", "mr_threshold", "sharpe", "total_return"]].to_string(index=False))
    
    return tuning_result


def demo_reinforcement_learning():
    """Demo 5: 强化学习训练（可选）"""
    print_section("Demo 5: 强化学习训练（快速演示）")
    
    try:
        from quant_agent.rl_trainer import train_rl_agent, evaluate_rl_agent
        
        print("\n注意：完整训练需要较长时间，这里使用较少的步数进行演示")
        
        train_data = DataConfig(
            symbol="AAPL",
            start=dt.date(2020, 1, 1),
            end=dt.date(2022, 1, 1),
        )
        
        test_data = DataConfig(
            symbol="AAPL",
            start=dt.date(2022, 1, 1),
            end=dt.date(2023, 1, 1),
        )
        
        print("\n训练PPO Agent (10000步，快速演示)...")
        model, info = train_rl_agent(
            data_cfg=train_data,
            algorithm="PPO",
            total_timesteps=10000,  # 快速演示，实际应该更多
            model_save_path="demo_output/rl_agent_demo.zip",
            verbose=0,
        )
        
        print("✓ 训练完成")
        
        print("\n评估Agent表现...")
        results = evaluate_rl_agent(
            model=model,
            data_cfg=test_data,
            num_episodes=3,
        )
        
        print(f"\nRL Agent评估结果:")
        print(f"  平均收益率: {results['mean_return']:.2%}")
        print(f"  收益率标准差: {results['std_return']:.2%}")
        print(f"  评估回合数: {results['num_episodes']}")
        
        return model, results
        
    except ImportError:
        print("\n⚠️  stable-baselines3未安装，跳过RL演示")
        print("   安装命令: pip install stable-baselines3[extra]")
        return None, None
    except Exception as e:
        print(f"\n⚠️  RL训练出错: {e}")
        print("   这可能是正常的，RL训练需要较长时间和更多资源")
        return None, None


def generate_summary_report(results_dict: dict):
    """生成总结报告"""
    print_section("项目功能总结")
    
    print("\n本项目实现了以下核心功能：")
    print("\n1. 🤖 智能Agent系统")
    print("   - 感知-决策-执行-评估完整循环")
    print("   - 模块化设计，易于扩展")
    
    print("\n2. 📊 多策略支持")
    print("   - 均值回归策略（基于z-score）")
    print("   - 动量策略（基于移动平均线）")
    print("   - 支持自定义策略扩展")
    
    print("\n3. 🎯 市场状态识别")
    print("   - 自动识别趋势市、震荡市等市场状态")
    print("   - 根据市场状态动态选择最优策略")
    print("   - 技术指标：ATR、ADX、布林带等")
    
    print("\n4. 💰 智能仓位管理")
    print("   - 凯利公式（基于胜率和盈亏比）")
    print("   - 风险平价（基于波动率）")
    print("   - 波动率目标仓位管理")
    
    print("\n5. 🔧 自动参数优化")
    print("   - 网格搜索自动寻找最优参数")
    print("   - 支持多种评价指标（夏普比率、收益率等）")
    
    print("\n6. 🤖 强化学习支持")
    print("   - 使用RL训练智能交易Agent")
    print("   - 支持PPO、A2C、DQN等多种算法")
    print("   - Gym接口，易于扩展")
    
    print("\n7. 📈 完整回测系统")
    print("   - 支持手续费、滑点等真实交易成本")
    print("   - 丰富的评价指标（收益率、夏普、回撤等）")
    print("   - 可视化净值曲线")
    
    print("\n8. 🌍 多市场支持")
    print("   - 美股、A股、港股、加密货币")
    print("   - 自动数据下载和缓存")
    
    print("\n" + "=" * 70)
    print("技术栈: Python, pandas, numpy, stable-baselines3, gymnasium")
    print("=" * 70)


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" " * 15 + "量化交易Agent - 简历展示Demo")
    print("=" * 70)
    print("\n本Demo将展示项目的核心功能，适合用于简历展示")
    print("=" * 70)
    
    # 创建输出目录
    os.makedirs("demo_output", exist_ok=True)
    
    results_summary = {}
    
    try:
        # Demo 1: 传统策略对比
        strategy_results, equity_curves = demo_traditional_strategies()
        results_summary["策略对比"] = strategy_results
        
        # Demo 2: 市场状态识别
        market_state, state_result = demo_market_state_detection()
        results_summary["市场状态"] = market_state
        
        # Demo 3: 智能仓位管理
        position_stats = demo_intelligent_position_sizing()
        results_summary["仓位管理"] = position_stats
        
        # Demo 4: 参数优化
        optimization_result = demo_parameter_optimization()
        results_summary["参数优化"] = optimization_result.best_run.backtest_result.stats
        
        # Demo 5: 强化学习（可选）
        rl_model, rl_results = demo_reinforcement_learning()
        if rl_results:
            results_summary["强化学习"] = rl_results
        
        # 生成总结报告
        generate_summary_report(results_summary)
        
        print("\n" + "=" * 70)
        print("✓ 所有Demo完成！")
        print("=" * 70)
        print("\n生成的文件:")
        print("  - demo_output/strategy_comparison.png: 策略对比图")
        if rl_model:
            print("  - demo_output/rl_agent_demo.zip: RL模型")
        print("\n这些结果可以用于简历展示！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置中文字体（如果需要）
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    main()

