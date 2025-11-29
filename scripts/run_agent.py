import datetime as dt
from typing import Optional

import matplotlib.pyplot as plt
import typer

from quant_agent.agent import run_agent
from quant_agent.config import AgentConfig, BacktestConfig, DataConfig, StrategyConfig

app = typer.Typer(help="Quant Trading Agent CLI")


@app.command()
def run(
    symbol: str = typer.Option("AAPL", help="标的代码，例如 AAPL"),
    strategy: str = typer.Option(
        "mean_reversion", "--strategy", "-s", help="策略名称：mean_reversion 或 momentum"
    ),
    start: str = typer.Option("2018-01-01", help="开始日期，格式 YYYY-MM-DD"),
    end: Optional[str] = typer.Option(None, help="结束日期，默认为今天"),
    plot: bool = typer.Option(True, help="是否绘制净值曲线"),
) -> None:
    """
    运行示例 Agent：下载数据 -> 生成信号 -> 回测 -> 打印统计指标。
    """
    start_date = dt.date.fromisoformat(start)
    end_date = dt.date.fromisoformat(end) if end else None

    data_cfg = DataConfig(symbol=symbol, start=start_date, end=end_date)
    strat_cfg = StrategyConfig(name=strategy)  # type: ignore[arg-type]
    bt_cfg = BacktestConfig()
    agent_cfg = AgentConfig(data=data_cfg, strategy=strat_cfg, backtest=bt_cfg)

    result = run_agent(agent_cfg)

    stats = result.backtest_result.stats
    typer.echo("=== Backtest Stats ===")
    for k, v in stats.items():
        typer.echo(f"{k:>16}: {v}")

    if plot:
        df = result.backtest_result.data
        eq_col = result.backtest_result.equity_curve_col

        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df[eq_col], label="Equity")
        plt.title(f"Equity Curve - {symbol} - {strategy}")
        plt.xlabel("Date")
        plt.ylabel("Equity")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    app()



