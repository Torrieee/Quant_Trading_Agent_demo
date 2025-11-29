"""
不同市场股票数据示例

展示如何使用不同市场的股票代码运行 Agent
"""

import datetime as dt

from quant_agent import TradingAgent, AgentConfig, BacktestConfig, DataConfig, StrategyConfig


# 不同市场的股票代码示例
SYMBOLS = {
    # 美股
    "美股": {
        "AAPL": "苹果",
        "MSFT": "微软",
        "GOOGL": "谷歌",
        "TSLA": "特斯拉",
        "AMZN": "亚马逊",
        "NVDA": "英伟达",
        "META": "Meta (Facebook)",
    },
    # A股（需要 .SS 或 .SZ 后缀）
    "A股": {
        "000001.SS": "平安银行",
        "000002.SZ": "万科A",
        "600000.SS": "浦发银行",
        "600519.SS": "贵州茅台",
        "000858.SZ": "五粮液",
    },
    # 港股（需要 .HK 后缀）
    "港股": {
        "0700.HK": "腾讯控股",
        "0941.HK": "中国移动",
        "1299.HK": "友邦保险",
    },
    # 其他市场
    "其他": {
        "BTC-USD": "比特币",
        "ETH-USD": "以太坊",
    },
}


def run_agent_for_symbol(symbol: str, symbol_name: str = ""):
    """为指定股票代码运行 Agent"""
    print(f"\n{'='*60}")
    print(f"运行 Agent: {symbol} {symbol_name}")
    print(f"{'='*60}")
    
    try:
        agent_cfg = AgentConfig(
            data=DataConfig(
                symbol=symbol,
                start=dt.date(2020, 1, 1),
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
        
        agent = TradingAgent(agent_cfg)
        result = agent.run()
        
        # 显示结果
        stats = result.backtest_result.stats
        print(f"\n回测结果:")
        print(f"  总收益率:   {stats.get('total_return', 0):>8.2%}")
        print(f"  年化收益率: {stats.get('annual_return', 0):>8.2%}")
        print(f"  夏普比率:   {stats.get('sharpe', 0):>8.4f}")
        print(f"  最大回撤:   {stats.get('max_drawdown', 0):>8.2%}")
        
        return result
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def main():
    """主函数：展示不同市场的数据使用"""
    print("=" * 60)
    print("不同市场股票数据示例")
    print("=" * 60)
    
    print("\n支持的市场和股票代码格式：")
    for market, symbols in SYMBOLS.items():
        print(f"\n{market}:")
        for code, name in symbols.items():
            print(f"  {code:15} - {name}")
    
    print("\n" + "=" * 60)
    print("示例：运行几个不同市场的股票")
    print("=" * 60)
    
    # 示例 1: 美股
    run_agent_for_symbol("MSFT", "(微软)")
    
    # 示例 2: A股（如果网络允许）
    # run_agent_for_symbol("600519.SS", "(贵州茅台)")
    
    # 示例 3: 港股
    # run_agent_for_symbol("0700.HK", "(腾讯控股)")
    
    print("\n" + "=" * 60)
    print("提示：")
    print("=" * 60)
    print("1. 美股代码：直接使用股票代码，如 AAPL, MSFT, TSLA")
    print("2. A股代码：需要添加后缀，如 600519.SS (上海) 或 000001.SZ (深圳)")
    print("3. 港股代码：需要添加 .HK 后缀，如 0700.HK")
    print("4. 加密货币：使用格式如 BTC-USD, ETH-USD")
    print("\n使用命令行工具：")
    print("  python -m scripts.run_agent --symbol MSFT --strategy mean_reversion --start 2020-01-01")
    print("  python -m scripts.run_agent --symbol 600519.SS --strategy mean_reversion --start 2020-01-01")


if __name__ == "__main__":
    main()

