# 量化交易 Agent 项目详细说明

## 项目概述

这是一个完整的量化交易 Agent 框架，实现了从数据获取、策略构建、回测执行到参数优化的全流程自动化。项目采用面向对象设计，核心是 `TradingAgent` 类，实现了经典的 Agent 循环：感知（Perceive）→ 决策（Decide）→ 执行（Act）→ 评估（Evaluate）。

## 技术栈

- **Python 3.11+**
- **核心库**：
  - `pandas` - 数据处理和分析
  - `numpy` - 数值计算
  - `yfinance` - 金融数据获取
  - `pydantic` - 配置管理和数据验证
  - `typer` - 命令行接口
  - `matplotlib` - 数据可视化
  - `scikit-learn` - 机器学习工具（用于特征工程）

## 项目架构

### 核心模块

1. **`data.py`** - 数据获取模块
   - 从 Yahoo Finance 获取多市场股票数据
   - 支持数据缓存，避免重复下载
   - 自动处理 MultiIndex 列格式

2. **`features.py`** - 特征工程模块
   - 计算技术指标（移动平均线、z-score 等）
   - 计算日收益率
   - 为策略提供特征数据

3. **`strategy.py`** - 策略模块
   - 均值回归策略（Mean Reversion）
   - 动量策略（Momentum）
   - 可扩展的策略框架

4. **`backtester.py`** - 回测引擎
   - 模拟交易执行
   - 计算关键指标（收益率、夏普比率、最大回撤等）
   - 生成净值曲线

5. **`agent.py`** - Agent 核心模块
   - `TradingAgent` 类：实现完整的 Agent 工作流
   - `run_agent()` 函数：便捷接口

6. **`optimizer.py`** - 参数优化模块
   - 网格搜索（Grid Search）
   - 自动选择最优参数组合
   - 体现 Agent 的智能决策能力

7. **`config.py`** - 配置管理
   - 使用 Pydantic 定义配置模型
   - 类型安全和自动验证

### CLI 工具

- **`scripts/run_agent.py`** - 单策略回测工具
- **`scripts/tune_agent.py`** - 自动调参工具

### Demo 脚本

- **`quick_demo.py`** - 快速演示
- **`demo.py`** - 完整功能演示
- **`examples_different_symbols.py`** - 多市场数据示例

## 核心特性

### 1. 智能 Agent 设计

`TradingAgent` 类实现了完整的 Agent 循环：

```python
agent = TradingAgent(config)
result = agent.run()  # 自动执行：感知 -> 决策 -> 执行 -> 评估
```

- **感知（Perceive）**：自动获取市场数据
- **决策（Decide）**：根据配置选择策略并生成交易信号
- **执行（Act）**：运行回测模拟交易
- **评估（Evaluate）**：分析回测结果并输出关键指标

### 2. 多市场数据支持

- 美股：AAPL, MSFT, TSLA 等
- A股：600519.SS, 000001.SZ 等
- 港股：0700.HK, 0941.HK 等
- 加密货币：BTC-USD, ETH-USD 等

### 3. 自动参数优化

通过网格搜索自动寻找最优策略参数，体现 Agent 的智能决策能力。

### 4. 可扩展架构

- 使用 Pydantic 进行配置管理
- 策略模块化设计，易于添加新策略
- 清晰的代码结构，便于维护和扩展

## 使用场景

1. **量化策略研究**：快速测试和验证交易策略
2. **参数优化**：自动寻找最优策略参数
3. **策略对比**：对比不同策略的表现
4. **学习工具**：理解量化交易和 Agent 系统设计

## 项目亮点

1. **完整的 Agent 实现**：不仅仅是回测工具，而是真正的智能 Agent 系统
2. **工程化设计**：使用现代 Python 工具（Pydantic, Typer）提高代码质量
3. **易于使用**：提供 CLI 工具和 Demo 脚本，降低使用门槛
4. **可扩展性**：清晰的模块化设计，便于添加新功能

## 技术亮点

- **类型安全**：使用 Pydantic 进行配置验证
- **代码规范**：遵循 Python 最佳实践
- **文档完善**：详细的代码注释和 README
- **错误处理**：完善的异常处理和日志记录

## 适用人群

- 量化交易初学者
- Python 开发者
- 对 Agent 系统设计感兴趣的研究者
- 需要量化项目经验的求职者

