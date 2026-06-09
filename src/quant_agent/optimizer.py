from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from .agent import AgentRunResult, run_agent
from .config import AgentConfig, BacktestConfig, DataConfig, StrategyConfig
from .data import download_ohlcv


MetricName = str


@dataclass
class TuningResult:
    best_config: AgentConfig
    best_run: AgentRunResult
    summary: pd.DataFrame  # 各参数组合的表现汇总表
    metric: MetricName


def _iter_param_combinations(
    grid: Dict[str, Iterable[Any]]
) -> Iterable[Dict[str, Any]]:
    """将参数网格 dict 展开为一系列参数组合。"""
    keys = list(grid.keys())
    values_product = product(*(grid[k] for k in keys))
    for values in values_product:
        yield dict(zip(keys, values))


def grid_search_on_strategy(
    data_cfg: DataConfig,
    base_bt_cfg: BacktestConfig,
    strategy_name: str,
    param_grid: Dict[str, Iterable[Any]],
    metric: MetricName = "sharpe",
) -> TuningResult:
    """
    在单一策略上做简单网格搜索，通过 metric(默认 sharpe) 选择最优参数。
    """
    # 先把数据下载一次复用，避免反复请求
    df = download_ohlcv(data_cfg, use_cache=True)

    records: List[Dict[str, Any]] = []
    best_score = float("-inf")
    best_cfg: AgentConfig | None = None
    best_run: AgentRunResult | None = None

    for params in _iter_param_combinations(param_grid):
        strat_cfg = StrategyConfig(name=strategy_name, **params)  # type: ignore[arg-type]
        agent_cfg = AgentConfig(data=data_cfg, strategy=strat_cfg, backtest=base_bt_cfg)

        run = run_agent(agent_cfg)
        stats = run.backtest_result.stats
        score = float(stats.get(metric, float("nan")))

        row = {
            "strategy": strategy_name,
            **params,
            **stats,
        }
        records.append(row)

        if score > best_score:
            best_score = score
            best_cfg = agent_cfg
            best_run = run

    summary = pd.DataFrame(records).sort_values(by=metric, ascending=False)

    assert best_cfg is not None and best_run is not None
    return TuningResult(
        best_config=best_cfg,
        best_run=best_run,
        summary=summary,
        metric=metric,
    )


__all__ = ["TuningResult", "grid_search_on_strategy"]



