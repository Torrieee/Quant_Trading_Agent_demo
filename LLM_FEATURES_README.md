# LLM Agent功能说明

## 🎉 新增功能

已为项目添加了**Function Calling**和**RAG（检索增强生成）**功能，大幅提升与大模型Agent岗位的匹配度！

---

## 📦 安装依赖

```bash
pip install openai langchain langchain-community faiss-cpu
```

或安装所有依赖：

```bash
pip install -r requirements.txt
```

---

## 🚀 核心功能

### 1. Function Calling ⭐⭐⭐⭐⭐

实现了5个交易相关的Function Calling工具：

1. **get_market_data** - 获取市场数据
2. **analyze_market_state** - 分析市场状态
3. **get_strategy_recommendation** - 获取策略推荐
4. **calculate_position_size** - 计算仓位大小
5. **run_backtest** - 运行回测

**特点**：
- 符合OpenAI Function Calling规范
- 可以直接调用，不需要LLM
- 完整的参数验证和错误处理

### 2. RAG系统 ⭐⭐⭐⭐

实现了基于向量数据库的RAG系统：

- 使用FAISS存储历史交易记录
- 支持语义检索相关经验
- 可以增强LLM的决策能力

**特点**：
- 使用LangChain和FAISS
- 支持从历史交易记录构建知识库
- 语义检索相关经验

### 3. LLM Agent集成 ⭐⭐⭐⭐⭐

完整的LLM Agent类，支持：

- 与OpenAI API集成
- Function Calling自动调用
- RAG增强生成
- 对话历史管理

---

## 📝 使用示例

### 示例1：Function Calling（不需要API key）

```python
from quant_agent.llm_agent import TradingFunctionCaller

# 创建Function Caller
caller = TradingFunctionCaller()

# 获取市场数据
result = caller.call_function(
    "get_market_data",
    {
        "symbol": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01"
    }
)
print(result)

# 分析市场状态
result = caller.call_function(
    "analyze_market_state",
    {"symbol": "AAPL", "lookback_days": 60}
)
print(result)
```

### 示例2：LLM Agent对话（需要API key）

```python
import os
from quant_agent.llm_agent import LLMTradingAgent

# 设置API key
os.environ["OPENAI_API_KEY"] = "your_api_key"

# 创建Agent
agent = LLMTradingAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-3.5-turbo",
    enable_function_calling=True,
    enable_rag=True
)

# 对话（自动调用Function）
response = agent.chat("请帮我分析AAPL的市场情况并给出交易建议")
print(response)
```

### 示例3：RAG系统

```python
from quant_agent.llm_agent import RAGSystem

# 创建RAG系统
rag = RAGSystem(api_key=os.getenv("OPENAI_API_KEY"))

# 构建知识库
trading_records = [
    {
        "symbol": "AAPL",
        "strategy": "mean_reversion",
        "date": "2023-01-15",
        "return": 0.025,
        "market_state": "ranging",
        "position": 0.5,
        "result": "盈利"
    }
]
rag.build_knowledge_base(trading_records)

# 检索相关经验
results = rag.retrieve_relevant_experience("震荡市场的策略", k=3)
```

---

## 🎯 运行完整示例

```bash
python examples_llm_agent.py
```

**注意**：
- Function Calling示例不需要API key
- LLM和RAG示例需要设置`OPENAI_API_KEY`环境变量

---

## 📊 功能对比

| 功能 | 之前 | 现在 |
|------|------|------|
| Agent架构 | ✅ | ✅ |
| 强化学习 | ✅ | ✅ |
| Function Calling | ❌ | ✅ |
| RAG | ❌ | ✅ |
| LLM集成 | ❌ | ✅ |

---

## 🎓 简历描述更新

现在可以在简历中添加：

**新增功能**：
- **Function Calling**：实现了5个交易相关的工具函数，支持LLM自动调用获取数据、分析市场、执行回测等
- **RAG系统**：基于向量数据库实现检索增强生成，从历史交易记录中检索相关经验，增强LLM决策能力
- **LLM Agent集成**：完整集成OpenAI API，支持Function Calling和RAG，实现智能对话和交易分析

**技术栈新增**：OpenAI API, LangChain, FAISS

---

## 💡 面试要点

### 如何介绍Function Calling？

"我实现了符合OpenAI规范的Function Calling功能，定义了5个交易相关的工具函数。LLM可以根据用户需求自动调用这些函数，比如获取市场数据、分析市场状态、运行回测等。这体现了大模型Agent的核心能力：理解用户意图，调用工具完成任务。"

### 如何介绍RAG？

"我实现了基于向量数据库的RAG系统，可以将历史交易记录转换为向量存储。当LLM需要做决策时，系统会检索相关的历史经验，增强LLM的决策能力。这解决了LLM缺乏领域知识的问题。"

---

## ⚠️ 注意事项

1. **API Key**：LLM功能需要OpenAI API key，可以在[OpenAI官网](https://platform.openai.com/)获取
2. **成本**：使用OpenAI API会产生费用，建议使用gpt-3.5-turbo降低成本
3. **可选依赖**：如果不需要LLM功能，Function Calling仍然可以独立使用

---

## 🔗 相关文档

- [OpenAI Function Calling文档](https://platform.openai.com/docs/guides/function-calling)
- [LangChain文档](https://python.langchain.com/)
- [FAISS文档](https://github.com/facebookresearch/faiss)

---

**现在你的项目已经具备了大模型Agent的核心功能！** 🚀




