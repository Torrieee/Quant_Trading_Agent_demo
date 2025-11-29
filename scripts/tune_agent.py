import datetime as dt

import typer

from quant_agent.config import AgentConfig, BacktestConfig, DataConfig
from quant_agent.optimizer import grid_search_on_strategy

app = typer.Typer(help="Quant Trading Agent Auto-tuning CLI")


@app.command()
def grid_search(
    symbol: str = typer.Option("AAPL", help="标的代码，例如 AAPL"),
    strategy: str = typer.Option(
        "mean_reversion", "--strategy", "-s", help="策略名称，例如 mean_reversion"
    ),
    start: str = typer.Option("2018-01-01", help="开始日期，格式 YYYY-MM-DD"),
    end: str = typer.Option("2025-01-01", help="结束日期，格式 YYYY-MM-DD"),
    metric: str = typer.Option(
        "sharpe", help="用于选择最优参数的评价指标，例如 sharpe 或 total_return"
    ),
) -> None:
    """
    对指定策略做简单网格搜索，自动寻找最优参数组合。
    """
    start_date = dt.date.fromisoformat(start)
    end_date = dt.date.fromisoformat(end)

    data_cfg = DataConfig(symbol=symbol, start=start_date, end=end_date)
    bt_cfg = BacktestConfig()

    # 这里给出一个示例网格：可根据实际需要修改或扩展
    if strategy == "mean_reversion":
        param_grid = {
            "mr_window": [10, 20, 30],
            "mr_threshold": [0.8, 1.0, 1.2],
        }
    else:
        # 动量策略示例
        param_grid = {
            "mom_short_window": [10, 20],
            "mom_long_window": [50, 100],
        }

    tuning_res = grid_search_on_strategy(
        data_cfg=data_cfg,
        base_bt_cfg=bt_cfg,
        strategy_name=strategy,
        param_grid=param_grid,
        metric=metric,
    )

    typer.echo("=== Grid Search Summary (Top 10) ===")
    typer.echo(tuning_res.summary.head(10).to_string(index=False))

    typer.echo("\n=== Best Config ===")
    best_cfg: AgentConfig = tuning_res.best_config
    typer.echo(best_cfg.model_dump_json(indent=2))

    typer.echo("\n=== Best Stats ===")
    for k, v in tuning_res.best_run.backtest_result.stats.items():
        typer.echo(f"{k:>16}: {v}")


if __name__ == "__main__":
    app()


