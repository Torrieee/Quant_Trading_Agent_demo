# Quant Trading Agent

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)


本项目是一个完整的量化交易 Agent 框架，实现了从数据获取、策略构建、回测执行到参数优化的自动化流程。核心基于面向对象设计，通过 `TradingAgent` 统一组织感知（Perceive）、决策（Decide）、执行（Act）、评估（Evaluate）等步骤。

## 1. 项目特性

* **Agent 架构设计**：实现标准的感知—决策—执行—评估循环；
* **多市场数据支持**：支持美股、A股、港股、加密货币等；
* **自动参数优化**：内置网格搜索；
* **可扩展策略框架**：支持均值回归、动量等策略；
* **完整回测系统**：包含收益率、夏普比率、最大回撤等指标；
* **强化学习支持**：使用RL训练智能交易Agent（PPO、A2C、DQN等算法）；
* **市场状态识别**：自动识别趋势市、震荡市等市场状态；
* **智能仓位管理**：凯利公式、风险平价等仓位管理方法；
* **工程化结构**：使用 Pydantic、Typer 等现代 Python 工具，模块化设计清晰。

---

## 2. 快速开始

### 2.1 克隆项目

```bash
git clone https://github.com/Torrieee/quant_trading_agent.git
cd quant-trading-agent
```

### 2.2 创建虚拟环境（推荐）

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 安装项目（开发模式）

```bash
pip install -e .
```

---

## 3. 使用示例

### 3.1 运行快速示例

```bash
python quick_demo.py
```

### 3.2 运行完整 Demo

```bash
python demo.py
```

### 3.3 运行简历展示Demo ⭐

```bash
python resume_demo.py
```

这是一个综合性的演示脚本，展示项目的所有核心功能，适合用于简历展示和技术面试。

### 3.4 运行单策略回测

```bash
python -m scripts.run_agent \
    --symbol AAPL \
    --strategy mean_reversion \
    --start 2020-01-01
```

### 3.5 参数优化示例

```bash
python -m scripts.tune_agent \
    --symbol AAPL \
    --strategy mean_reversion \
    --start 2020-01-01 \
    --end 2023-01-01 \
    --metric sharpe
```

---

## 4. 项目结构

```
quant_agent/
├── src/
│   └── quant_agent/
│       ├── agent.py          # TradingAgent 类（核心）
│       ├── data.py           # 数据获取模块
│       ├── features.py       # 特征工程
│       ├── strategy.py       # 策略定义
│       ├── backtester.py     # 回测引擎
│       ├── optimizer.py      # 参数优化
│       └── config.py         # 配置管理
├── scripts/
│   ├── run_agent.py          # 策略回测入口
│   └── tune_agent.py         # 参数优化入口
├── demo.py
├── quick_demo.py
├── examples_different_symbols.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 5. 主要功能说明

### 5.1 TradingAgent 类

```python
from quant_agent import (
    TradingAgent, AgentConfig, DataConfig,
    StrategyConfig, BacktestConfig
)
import datetime as dt

config = AgentConfig(
    data=DataConfig(symbol="AAPL", start=dt.date(2020, 1, 1)),
    strategy=StrategyConfig(name="mean_reversion"),
    backtest=BacktestConfig(initial_cash=100000)
)

agent = TradingAgent(config)
result = agent.run()
```

### 5.2 支持的数据源

* 美股：AAPL、MSFT、TSLA、GOOGL、NVDA 等
* A股：600519.SS、000001.SZ 等
* 港股：0700.HK、0941.HK 等
* 加密货币：BTC-USD、ETH-USD 等

### 5.3 内置策略

* 均值回归（mean_reversion）
* 动量策略（momentum）

### 5.4 回测指标

* 总收益率（Total Return）
* 年化收益率（Annual Return）
* 夏普比率（Sharpe Ratio）
* 最大回撤（Max Drawdown）
* 胜率（Win Rate）
* 交易次数（Number of Trades）

### 5.5 强化学习训练

使用强化学习训练智能交易Agent：

```python
from quant_agent import DataConfig
from quant_agent.rl_trainer import train_rl_agent, evaluate_rl_agent
import datetime as dt

# 训练RL Agent
train_data = DataConfig(symbol="AAPL", start=dt.date(2020, 1, 1), end=dt.date(2022, 1, 1))
model, info = train_rl_agent(
    data_cfg=train_data,
    algorithm="PPO",
    total_timesteps=50000,
    model_save_path="models/rl_agent.zip",
)

# 评估Agent
test_data = DataConfig(symbol="AAPL", start=dt.date(2022, 1, 1), end=dt.date(2023, 1, 1))
results = evaluate_rl_agent(model=model, data_cfg=test_data)
print(f"平均收益率: {results['mean_return']:.2%}")
```

支持的算法：PPO、A2C、DQN、SAC、TD3

详细文档请参考：`RL_GUIDE.md`

---

## 6. 技术栈

* Python 3.11+
* pandas - 数据处理
* numpy - 数值计算
* yfinance - 金融数据获取
* pydantic - 配置管理
* typer - 命令行接口
* matplotlib - 数据可视化
* **gymnasium** - 强化学习环境
* **stable-baselines3** - RL算法库

---


## 7. 贡献指南

欢迎提交 Issue 或 Pull Request。

---

## 8. 许可证

本项目基于 MIT License 开源，详情见 `LICENSE` 文件。

---

## 9. 作者

Torrie Li
GitHub: [https://github.com/Torrieee](https://github.com/Torrieee)

---

如果这个项目对你有帮助，请给个 Star！
