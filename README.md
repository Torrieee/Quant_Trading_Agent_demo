# Quant Trading Agent

[![CI](https://github.com/Torrieee/Quant_Trading_Agent_demo/actions/workflows/ci.yml/badge.svg)](https://github.com/Torrieee/Quant_Trading_Agent_demo/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

本项目是一个完整的量化交易 Agent 框架，实现了从数据获取、策略构建、回测执行到参数优化的自动化流程。核心基于面向对象设计，通过 `TradingAgent` 统一组织感知（Perceive）、决策（Decide）、执行（Act）、评估（Evaluate）等步骤。

在此基础上扩展了 **Agent Quality Harness**：YAML 驱动用例、JSON 评估报告、离线质量门禁（`--gate`）与 GitHub Actions CI，面向 AI Agent 研发质量效能场景（结果完整性 / 流程 trace / LLM tool schema 契约）。

## 1. 项目特性

* **Agent 架构设计**：实现标准的感知—决策—执行—评估循环；
* **多市场数据支持**：支持美股、A股、港股、加密货币等；
* **自动参数优化**：内置网格搜索；
* **可扩展策略框架**：支持均值回归、动量等策略；
* **完整回测系统**：包含收益率、夏普比率、最大回撤等指标；
* **强化学习支持**：使用RL训练智能交易Agent（PPO、A2C、DQN等算法）；
* **市场状态识别**：自动识别趋势市、震荡市等市场状态；
* **智能仓位管理**：凯利公式、风险平价等仓位管理方法；
* **工程化结构**：使用 Pydantic、Typer 等现代 Python 工具，模块化设计清晰；
* **Agent 质量效能体系**：`harness/` 离线评估 + `tool_compliance` schema 契约测试 + CI 质量门禁（Gate 不以 Sharpe 等盈亏指标作为门禁）。

---

## 2. 快速开始

### 2.1 克隆项目

```bash
git clone https://github.com/Torrieee/Quant_Trading_Agent_demo.git
cd Quant_Trading_Agent_demo
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
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

或一条命令（含开发依赖）：

```bash
pip install -e ".[dev]"
```

**Windows 推荐**（避免 conda/venv 混用导致 `pytest` 找不到 numpy）：

```powershell
.\setup.ps1
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

> 若提示符同时有 `(base)` 和 `(venv)`，先 `deactivate` 直到只剩一个环境；安装与测试务必用**同一个** Python：`python -m pip install ...` + `python -m pytest`。

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

### 3.3 简历展示 Demo

```bash
python demo.py
python examples_llm_agent.py
```

`demo.py` 展示规则 Agent 回测与优化；`examples_llm_agent.py` 展示 LLM Function Calling 集成。适合简历展示与技术面试。

### 3.4 运行质量 Harness（离线 + 质量门禁）

```bash
python -m pytest tests/ -v
python scripts/run_harness.py --report reports/harness_report.json
python scripts/run_harness.py --gate
```

`--gate` 在 schema / process / tool 结构性检查失败时 exit 1；**不以 Sharpe 等盈亏指标作为门禁**。

### 3.5 运行单策略回测

```bash
python -m scripts.run_agent \
    --symbol AAPL \
    --strategy mean_reversion \
    --start 2020-01-01
```

### 3.6 参数优化示例

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
Quant_Trading_Agent_demo/
├── .github/workflows/ci.yml  # GitHub Actions：pytest + harness gate
├── src/quant_agent/
│   ├── agent.py              # TradingAgent（Perceive-Decide-Act-Evaluate）
│   ├── backtester.py         # 回测引擎
│   ├── llm_agent.py          # LLM Function Calling
│   ├── harness/              # Agent Quality Harness
│   │   ├── cases/            # YAML 用例
│   │   └── evaluators/       # 结果 / 流程 / tool 合规
│   └── ...
├── tests/                      # backtester / pipeline / tool_compliance
├── scripts/
│   ├── run_agent.py
│   ├── tune_agent.py
│   └── run_harness.py          # 质量 Harness + --gate
├── setup.ps1                   # Windows 一键建 .venv
├── demo.py
├── requirements.txt
└── pyproject.toml
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

详细用法见 `examples_rl_training.py`。

---

## 6. Agent 质量效能体系

Quant Trading Agent 是**被测系统**，`harness/` 是**质量层**（思路类似飞书 AI Harness：多维评估 + 离线可跑 + CI 门禁）。

### 6.1 三维评估（Gate 不看盈亏）

| 维度 | 验证什么 | Gate 检查 |
|------|----------|-----------|
| **结果完整性** | stats 字段齐全、无 NaN | `result_schema_valid`, `no_nan_metrics`, `num_days_valid` |
| **流程 trace** | perceive→decide→act→evaluate | phase 级 `process_trace`，每步 `output_keys` 非空 |
| **tool_compliance** | LLM 工具 schema 契约 | 6 项确定性检查（见下） |

盈亏指标（Sharpe、回撤等）写入 JSON 报告的 `report_only` 段，**不参与 exit 1**。

### 6.2 亮点：tool_compliance（schema 契约测试）

对 `TradingFunctionCaller.get_available_functions()` 做 **确定性** 检查，比「LLM 是否选对 tool」更适合 CI：

- `schema_fields_present` — name / description / parameters
- `required_args_present` — required 字段声明正确
- `enum_values_valid` — enum 约束合法
- `mock_arguments_parseable` — mock 参数可执行
- `handler_returns_expected_keys` — 路由返回预期结构
- `invalid_arguments_raise_clear_error` — 非法参数返回明确错误

### 6.3 本地运行与 CI

```bash
python -m pytest tests/ -v
python scripts/run_harness.py --report reports/harness_report.json
python scripts/run_harness.py --gate
```

推送至 `main` 后，[GitHub Actions](https://github.com/Torrieee/Quant_Trading_Agent_demo/actions) 自动执行相同检查（pytest + harness gate）。

---

## 7. 技术栈

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


## 8. 贡献指南

欢迎提交 Issue 或 Pull Request。

---

## 9. 许可证

本项目基于 MIT License 开源，详情见 `LICENSE` 文件。

---

## 10. 作者

Torrie Li
GitHub: [https://github.com/Torrieee](https://github.com/Torrieee)

---

如果这个项目对你有帮助，请给个 Star！
