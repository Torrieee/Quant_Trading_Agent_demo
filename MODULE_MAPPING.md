# Agent模块与Python文件对应关系

## 四个核心模块的文件位置

### 1. 感知模块（Perceive）
**方法定义**：`src/quant_agent/agent.py` - `TradingAgent.perceive()` (第37-44行)
```python
def perceive(self):
    """Agent 感知环境：获取市场数据。"""
    self.data = download_ohlcv(self.config.data)
    return self.data
```

**实际功能实现**：`src/quant_agent/data.py` - `download_ohlcv()` (第18行)
- 功能：下载或读取缓存的OHLCV数据
- 支持多市场：美股、A股、港股、加密货币
- 数据缓存机制：避免重复下载

---

### 2. 决策模块（Decide）
**方法定义**：`src/quant_agent/agent.py` - `TradingAgent.decide()` (第46-56行)
```python
def decide(self):
    """Agent 决策：根据配置和当前数据选择策略并生成交易信号。"""
    self.strategy_result = build_strategy(self.data, self.config.strategy)
    return self.strategy_result
```

**实际功能实现**：`src/quant_agent/strategy.py` - `build_strategy()` (第73行)
- 功能：根据策略配置生成交易信号
- 支持策略：均值回归、动量策略
- 特征工程：在 `strategy.py` 的 `prepare_features()` 中实现

**相关文件**：
- `src/quant_agent/features.py` - 技术指标计算（移动平均、z-score等）
- `src/quant_agent/market_state.py` - 市场状态识别（用于动态策略选择）

---

### 3. 执行模块（Act）
**方法定义**：`src/quant_agent/agent.py` - `TradingAgent.act()` (第58-73行)
```python
def act(self):
    """Agent 执行：运行回测，模拟交易执行。"""
    self.backtest_result = run_backtest(
        self.strategy_result.data,
        signal_col=self.strategy_result.signal_col,
        cfg=self.config.backtest,
    )
    return self.backtest_result
```

**实际功能实现**：`src/quant_agent/backtester.py` - `run_backtest()` (第16行)
- 功能：模拟交易执行，计算收益和风险指标
- 考虑因素：手续费、仓位管理、交易成本
- 输出：净值曲线、收益率、夏普比率、最大回撤等

---

### 4. 评估模块（Evaluate）
**方法定义**：`src/quant_agent/agent.py` - `TradingAgent.evaluate()` (第75-84行)
```python
def evaluate(self) -> dict:
    """Agent 评估：分析回测结果，返回关键指标。"""
    stats = self.backtest_result.stats
    return stats
```

**实际功能实现**：
- 统计指标计算：`src/quant_agent/backtester.py` - `run_backtest()` (第44-65行)
  - 计算总收益率、年化收益率、夏普比率、最大回撤等
- 参数优化：`src/quant_agent/optimizer.py` - `grid_search_on_strategy()`
  - 网格搜索自动寻找最优参数

---

## 完整调用链

```
agent.py (TradingAgent.run())
    │
    ├─→ perceive()
    │   └─→ data.py (download_ohlcv())
    │       └─→ 获取市场数据
    │
    ├─→ decide()
    │   └─→ strategy.py (build_strategy())
    │       ├─→ features.py (技术指标计算)
    │       └─→ 生成交易信号
    │
    ├─→ act()
    │   └─→ backtester.py (run_backtest())
    │       └─→ 模拟交易执行
    │
    └─→ evaluate()
        └─→ backtester.py (stats计算)
            └─→ 分析性能指标
```

---

## 文件结构总结

### 核心Agent文件
- **`agent.py`** - TradingAgent类，包含四个核心方法（perceive, decide, act, evaluate）

### 功能模块文件
- **`data.py`** - 感知模块：数据获取和缓存
- **`strategy.py`** - 决策模块：策略构建和信号生成
- **`backtester.py`** - 执行模块：交易模拟和统计计算
- **`features.py`** - 特征工程：技术指标计算
- **`optimizer.py`** - 评估模块：参数优化

### 增强功能文件
- **`market_state.py`** - 市场状态识别（用于智能决策）
- **`position_sizing.py`** - 智能仓位管理（用于执行优化）
- **`rl_env.py`** - 强化学习环境
- **`rl_trainer.py`** - 强化学习训练

### 配置文件
- **`config.py`** - 配置管理（Pydantic模型）

---

## 面试回答建议

**如果被问到"这四个模块分别在哪个文件中？"**

**标准回答**：
"四个模块的方法定义都在 `agent.py` 的 `TradingAgent` 类中，但实际功能实现分散在不同的模块文件中：

1. **感知模块**：`agent.py` 的 `perceive()` 方法调用 `data.py` 的 `download_ohlcv()` 函数获取市场数据
2. **决策模块**：`agent.py` 的 `decide()` 方法调用 `strategy.py` 的 `build_strategy()` 函数生成交易信号
3. **执行模块**：`agent.py` 的 `act()` 方法调用 `backtester.py` 的 `run_backtest()` 函数模拟交易
4. **评估模块**：`agent.py` 的 `evaluate()` 方法直接使用 `backtester.py` 计算的统计指标

这种设计实现了关注点分离：`agent.py` 负责协调流程，各个功能模块负责具体实现，便于维护和扩展。"

---

## 代码行数参考

- `agent.py`: 132行（包含四个核心方法）
- `data.py`: 98行（感知功能）
- `strategy.py`: 91行（决策功能）
- `backtester.py`: 74行（执行和评估功能）




