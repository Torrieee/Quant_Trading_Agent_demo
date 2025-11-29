# Quant Trading Agent

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个完整的量化交易 Agent 框架，实现了从数据获取、策略构建、回测执行到参数优化的全流程自动化。项目采用面向对象设计，核心是 `TradingAgent` 类，实现了经典的 Agent 循环：**感知（Perceive）→ 决策（Decide）→ 执行（Act）→ 评估（Evaluate）**。

## ✨ 核心特性

- 🤖 **智能 Agent 系统**：`TradingAgent` 类实现完整的感知-决策-执行-评估循环
- 📊 **多市场数据支持**：支持美股、A股、港股、加密货币等多个市场
- 🔧 **自动参数优化**：通过网格搜索自动寻找最优策略参数
- 📈 **策略框架**：内置均值回归、动量等策略，易于扩展
- 🎯 **回测引擎**：完整的回测系统，支持多种评价指标
- 🛠️ **工程化设计**：使用 Pydantic、Typer 等现代 Python 工具

## 🚀 快速开始

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/quant-trading-agent.git
cd quant-trading-agent

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装项目
pip install -e .
```

### 快速演示

```bash
# 运行快速 Demo
python quick_demo.py

# 运行完整 Demo（包含策略对比、参数优化等）
python demo.py
```

### 使用示例

```bash
# 单策略回测
python -m scripts.run_agent --symbol AAPL --strategy mean_reversion --start 2020-01-01

# 自动参数优化
python -m scripts.tune_agent --symbol AAPL --strategy mean_reversion --start 2020-01-01 --end 2023-01-01 --metric sharpe

# 不同市场示例
python examples_different_symbols.py
```

## 📁 项目结构

```
quant_agent/
├── src/
│   └── quant_agent/          # 核心模块
│       ├── agent.py          # TradingAgent 类
│       ├── data.py           # 数据获取
│       ├── features.py       # 特征工程
│       ├── strategy.py        # 策略定义
│       ├── backtester.py      # 回测引擎
│       ├── optimizer.py      # 参数优化
│       └── config.py          # 配置管理
├── scripts/                   # CLI 工具
│   ├── run_agent.py          # 单策略回测
│   └── tune_agent.py          # 自动调参
├── demo.py                    # 完整 Demo
├── quick_demo.py              # 快速 Demo
├── examples_different_symbols.py  # 多市场示例
├── requirements.txt           # 依赖列表
├── pyproject.toml            # 项目配置
└── README.md                 # 项目说明
```

## 🎯 核心功能

### 1. TradingAgent 类

```python
from quant_agent import TradingAgent, AgentConfig, DataConfig, StrategyConfig, BacktestConfig
import datetime as dt

# 配置 Agent
config = AgentConfig(
    data=DataConfig(symbol="AAPL", start=dt.date(2020, 1, 1)),
    strategy=StrategyConfig(name="mean_reversion"),
    backtest=BacktestConfig(initial_cash=100000)
)

# 创建并运行 Agent
agent = TradingAgent(config)
result = agent.run()  # 自动执行：感知 -> 决策 -> 执行 -> 评估
```

### 2. 支持的数据源

- **美股**：`AAPL`, `MSFT`, `TSLA`, `GOOGL`, `NVDA` 等
- **A股**：`600519.SS` (上海), `000001.SZ` (深圳) 等
- **港股**：`0700.HK` (腾讯), `0941.HK` (中国移动) 等
- **加密货币**：`BTC-USD`, `ETH-USD` 等

### 3. 内置策略

- **均值回归策略（mean_reversion）**：基于 z-score 的均值回归
- **动量策略（momentum）**：基于移动平均线的趋势跟随

### 4. 回测指标

- 总收益率（Total Return）
- 年化收益率（Annual Return）
- 夏普比率（Sharpe Ratio）
- 最大回撤（Max Drawdown）
- 胜率（Win Rate）
- 交易次数（Number of Trades）

## 🔧 技术栈

- **Python 3.11+**
- **pandas** - 数据处理
- **numpy** - 数值计算
- **yfinance** - 金融数据获取
- **pydantic** - 配置管理和数据验证
- **typer** - 命令行接口
- **matplotlib** - 数据可视化

## 📚 文档

- [项目详细说明](PROJECT_DESCRIPTION.md)
- [简历描述建议](RESUME_GUIDE.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 👤 作者

[Your Name] - [GitHub](https://github.com/YOUR_USERNAME)

**注意**：请将 `YOUR_USERNAME` 替换为你的实际 GitHub 用户名

## 🙏 致谢

- 数据来源：[Yahoo Finance](https://finance.yahoo.com/)
- 感谢所有开源社区的支持






下面是给你**去掉所有图标 / 徽章 / emoji** 的 **专业版 README**，保持技术性强、结构清晰、内容严谨，适合放在 GitHub 上展示一个工程化量化交易项目。

你可以直接复制粘贴覆盖你的 README.md。

---

# Quant Trading Agent

本项目是一个完整的量化交易 Agent 框架，实现了从数据获取、策略构建、回测执行到参数优化的自动化流程。核心基于面向对象设计，通过 `TradingAgent` 统一组织感知（Perceive）、决策（Decide）、执行（Act）、评估（Evaluate）等步骤。

## 1. 项目特性

* **Agent 架构设计**：实现标准的感知—决策—执行—评估循环；
* **多市场数据支持**：支持美股、A股、港股、加密货币等；
* **自动参数优化**：内置网格搜索；
* **可扩展策略框架**：支持均值回归、动量等策略；
* **完整回测系统**：包含收益率、夏普比率、最大回撤等指标；
* **工程化结构**：使用 Pydantic、Typer 等现代 Python 工具，模块化设计清晰。

---

## 2. 快速开始

### 2.1 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/quant-trading-agent.git
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

### 3.3 运行单策略回测

```bash
python -m scripts.run_agent \
    --symbol AAPL \
    --strategy mean_reversion \
    --start 2020-01-01
```

### 3.4 参数优化示例

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

---

## 6. 技术栈

* Python 3.11+
* pandas
* numpy
* yfinance
* pydantic
* typer
* matplotlib

---

## 7. 文档

* `PROJECT_DESCRIPTION.md`
* `RESUME_GUIDE.md`

---

## 8. 贡献指南

欢迎提交 Issue 或 Pull Request。

---

## 9. 许可证

本项目基于 MIT License 开源，详情见 `LICENSE` 文件。

---

## 10. 作者

YOUR NAME
GitHub: [https://github.com/YOUR_USERNAME](https://github.com/YOUR_USERNAME)

请将 `YOUR_USERNAME` 替换为你的实际用户名。


---

如果这个项目对你有帮助，请给个 Star！
