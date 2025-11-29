"""
增强版 Agent 使用示例

展示如何使用市场状态识别和智能仓位管理功能
"""

import datetime as dt

from quant_agent import TradingAgent, AgentConfig, BacktestConfig, DataConfig, StrategyConfig
from quant_agent.market_state import identify_market_state, get_optimal_strategy_for_regime
from quant_agent.position_sizing import (
    kelly_position_size,
    risk_parity_position_size,
    calculate_trade_statistics,
)


def example_market_state_detection():
    """示例1：市场状态识别和动态策略选择"""
    print("=" * 60)
    print("示例1：市场状态识别和动态策略选择")
    print("=" * 60)
    
    # 配置Agent
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2024, 1, 1),
    )
    
    # 先获取数据
    from quant_agent.data import download_ohlcv
    df = download_ohlcv(data_cfg)
    
    # 识别市场状态
    market_state = identify_market_state(df)
    
    print(f"\n当前市场状态:")
    print(f"  状态类型: {market_state.regime.value}")
    print(f"  波动率: {market_state.volatility:.2%}")
    print(f"  趋势强度: {market_state.trend_strength:.2f}")
    print(f"  ADX: {market_state.adx:.2f}")
    print(f"  是否看涨: {market_state.is_bullish}")
    print(f"  是否看跌: {market_state.is_bearish}")
    
    # 根据市场状态推荐策略
    recommended_strategy = get_optimal_strategy_for_regime(market_state)
    print(f"\n推荐策略: {recommended_strategy}")
    
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
    
    print(f"\n回测结果:")
    print(f"  总收益率: {result.backtest_result.stats['total_return']:.2%}")
    print(f"  夏普比率: {result.backtest_result.stats['sharpe']:.4f}")
    print(f"  最大回撤: {result.backtest_result.stats['max_drawdown']:.2%}")


def example_intelligent_position_sizing():
    """示例2：智能仓位管理"""
    print("\n" + "=" * 60)
    print("示例2：智能仓位管理")
    print("=" * 60)
    
    # 先运行一个策略获取交易统计
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2024, 1, 1),
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
    
    # 使用凯利公式计算最优仓位
    if trade_stats['num_trades'] > 0:
        kelly_position = kelly_position_size(
            win_rate=trade_stats['win_rate'],
            avg_win=trade_stats['avg_win'],
            avg_loss=trade_stats['avg_loss'],
            kelly_fraction=0.25  # 使用1/4凯利，更保守
        )
        print(f"\n凯利公式建议仓位: {kelly_position:.2%}")
    
    # 使用风险平价计算仓位
    market_state = identify_market_state(result.strategy_result.data)
    risk_parity_position = risk_parity_position_size(
        volatility=market_state.volatility,
        target_volatility=0.15,  # 目标15%波动率
        max_position=1.0
    )
    print(f"风险平价建议仓位: {risk_parity_position:.2%}")
    
    # 对比固定仓位
    print(f"\n固定仓位（当前）: {backtest_cfg.max_position:.2%}")
    print(f"\n建议: 根据市场状态和交易表现，可以动态调整仓位")


def example_adaptive_agent():
    """示例3：自适应Agent - 结合市场状态和仓位管理"""
    print("\n" + "=" * 60)
    print("示例3：自适应Agent")
    print("=" * 60)
    
    data_cfg = DataConfig(
        symbol="AAPL",
        start=dt.date(2020, 1, 1),
        end=dt.date(2024, 1, 1),
    )
    
    # 获取数据并识别市场状态
    from quant_agent.data import download_ohlcv
    df = download_ohlcv(data_cfg)
    market_state = identify_market_state(df)
    
    # 根据市场状态选择策略
    strategy_name = get_optimal_strategy_for_regime(market_state)
    strategy_cfg = StrategyConfig(name=strategy_name)
    
    # 根据波动率调整仓位（高波动时降低仓位）
    if market_state.volatility > 0.3:
        max_position = 0.5  # 高波动时最多50%仓位
    elif market_state.volatility > 0.2:
        max_position = 0.75  # 中等波动时75%仓位
    else:
        max_position = 1.0  # 低波动时可以满仓
    
    backtest_cfg = BacktestConfig(
        initial_cash=100000,
        max_position=max_position,
    )
    
    agent_cfg = AgentConfig(
        data=data_cfg,
        strategy=strategy_cfg,
        backtest=backtest_cfg,
    )
    
    print(f"\n自适应配置:")
    print(f"  市场状态: {market_state.regime.value}")
    print(f"  波动率: {market_state.volatility:.2%}")
    print(f"  选择策略: {strategy_name}")
    print(f"  最大仓位: {max_position:.2%}")
    
    agent = TradingAgent(agent_cfg)
    result = agent.run()
    
    print(f"\n回测结果:")
    print(f"  总收益率: {result.backtest_result.stats['total_return']:.2%}")
    print(f"  年化收益率: {result.backtest_result.stats['annual_return']:.2%}")
    print(f"  夏普比率: {result.backtest_result.stats['sharpe']:.4f}")
    print(f"  最大回撤: {result.backtest_result.stats['max_drawdown']:.2%}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("增强版 Agent 功能演示")
    print("=" * 60)
    print("\n本示例将展示以下增强功能：")
    print("1. 市场状态识别和动态策略选择")
    print("2. 智能仓位管理（凯利公式、风险平价）")
    print("3. 自适应Agent（结合市场状态和仓位管理）")
    print("=" * 60)
    
    try:
        example_market_state_detection()
        example_intelligent_position_sizing()
        example_adaptive_agent()
        
        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("=" * 60)
        print("\n💡 提示：")
        print("- 市场状态识别可以帮助Agent自动选择最适合的策略")
        print("- 智能仓位管理可以根据风险和收益动态调整仓位")
        print("- 结合使用可以显著提升Agent的智能化水平")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

