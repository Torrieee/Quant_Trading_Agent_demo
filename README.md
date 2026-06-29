# Quant Trading Agent

[![CI](https://github.com/Torrieee/Quant_Trading_Agent_demo/actions/workflows/ci.yml/badge.svg)](https://github.com/Torrieee/Quant_Trading_Agent_demo/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

面向 **Agent 开发 / 量化研究** 场景的 **Agentic Workflow** Demo：在经典量化回测能力之上，提供 **LangGraph 固定拓扑编排 + 专用 Agent 节点（ReAct）+ RAG 证据层 + 分层 Agent 评测**。

**产品入口**：`QuantEngine.analyze()` → `AgentCoordinator`（LangGraph）  
**评测入口**：`scripts/run_eval.py`（离线回归 + 可选 Live 能力评测）

> 详细架构见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)；评测说明见 [`docs/EVAL.md`](docs/EVAL.md)；变更记录见 [`docs/UPDATE_LOG.md`](docs/UPDATE_LOG.md)。

---

## 1. 核心能力

| 模块 | 说明 |
|------|------|
| **Agentic 工作流** | 固定拓扑 + 代码 Supervisor 路由：`analysis_panel → document_retrieval → research → [reflection] → risk → reporter` |
| **节点类型** | 规则节点（`analysis_panel`）、检索节点（`document_retrieval`）、Agent 节点（Research/Risk 的 ReAct）、报告节点（`reporter`） |
| **ReAct 工具** | Research / Risk 通过 `react_loop` 由模型决定工具调用与停止 |
| **Evidence / RAG** | SEC/seed/profile + Hybrid 检索 + episodic/semantic memory + `document_signal` 决策修正 |
| **HITL** | Demo 用 `interrupt_before=["risk"]` + checkpoint；`QuantEngine.resume()` 继续（正式审批可升级为节点内 `interrupt()`） |
| **可观测** | `trace_steps`、JSON trace 导出、可选 Langfuse |
| **合规 / 模拟盘** | `audit_log`、`guardrails`、paper trading 工具 |
| **Agent Eval** | 三层：`regression_v1` 锁 harness / `capability_v1` 测真实策略 / `reliability_v1` 测故障恢复 |
| **Context Engine** | `context/` 模块：token 预算、去重、来源配额、`context_manifest` |
| **Retrieval Eval** | `retrieval_v1`（Recall@K / MRR 消融，无 LLM） |
| **经典量化** | `TradingAgent` 回测、参数优化 |

---

## 2. 快速开始

### 2.1 克隆与安装

```bash
git clone https://github.com/Torrieee/Quant_Trading_Agent_demo.git
cd Quant_Trading_Agent_demo
```

**Windows（推荐）**

```powershell
.\setup.ps1
.\.venv\Scripts\Activate.ps1
```

**通用**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

复制环境变量模板并按需填写：

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

### 2.2 运行测试与离线评测（无需 API Key）

```bash
python -m pytest tests/ -v -m "not integration" --ignore=tests/test_runtime_integration.py
python scripts/run_eval.py
```

离线回归 **15/15** 应全部通过；报告输出至 `reports/eval_regression_v1.json`。

> **评测分层**：Fake Model 回归锁定 **harness / 编排 / 状态传递**；`capability_v1`（`--live`）才评估真实模型的 **工具选择与重规划**；`reliability_v1` 在 Fake Model 下测 **故障恢复**，不用 `pass^k` 冒充 Agent 策略稳定性。

### 2.3 多智能体在线分析（需 DeepSeek）

```bash
# .env 中设置 DEEPSEEK_API_KEY
python examples_multi_agent.py
```

`scripts/run_runtime_agent.py` 是内部 runtime case 联调入口，当前不作为快速开始推荐命令；日常在线分析请使用 `examples_multi_agent.py` 或直接调用 `QuantEngine`。

### 2.4 Streamlit 控制台（推荐）

```bash
pip install -e ".[ui]"
python scripts/run_dashboard.py
```

浏览器打开 `http://localhost:8501`，三页：

| 页面 | 用途 |
|------|------|
| **分析工作台** | 跑全链路、动态 Research、HITL、Context 预算 |
| **评测中心** | 一键跑 regression / retrieval / reliability |
| **记忆与上下文** | 查看 memory_meta、semantic、检索结果 |

详细测试步骤见 [docs/UI_GUIDE.md](docs/UI_GUIDE.md)。

- **Demo 模式**：本地 fixture + 模拟 LLM，无需 API Key（默认）  
- **在线模式**：配置 `DEEPSEEK_API_KEY` 后关闭 Demo 开关

---

## 3. Agent 评测

| Evalset | 模式 | 用途 | CI |
|---------|------|------|-----|
| `evalsets/regression_v1.yaml` | offline（`RoleAwareFakeModel`） | 确定性回归，测编排/工具/RAG/记忆/风控/HITL | **每次 PR**（`quality` job） |
| `evalsets/capability_v1.yaml` | live（DeepSeek） | 真实推理能力 + 可选 LLM Judge | **定时/手动**（`eval-live` job，需 secret） |

```bash
# 离线回归（默认）
python scripts/run_eval.py

# Live 能力评测
python scripts/run_eval.py --live --judge
```

GitHub Actions 需在仓库 Secrets 配置 `DEEPSEEK_API_KEY` 后才会跑 Live job；未配置时自动跳过，不导致 CI 失败。

详见 [`docs/EVAL.md`](docs/EVAL.md)。

---

## 4. CI 流水线

`.github/workflows/ci.yml` 包含两个 job：

1. **`quality`**（每次 push/PR）  
   - `pytest -m "not integration"`  
   - `python scripts/run_eval.py`（`regression_v1`）  
   - `python scripts/run_retrieval_eval.py`（`retrieval_v1`）  
   - `python scripts/run_reliability_eval.py`（`reliability_v1`）  
   - 上传 `eval-regression-v1` artifact  

2. **`eval-live`**（push、定时周一、workflow_dispatch；同仓库 PR 也会触发）  
   - 有 `DEEPSEEK_API_KEY` 时跑 `capability_v1` + Judge  
   - 上传 `eval-capability-v1` artifact  

---

## 5. 项目结构

```
Quant_Trading_Agent_demo/
├── .github/workflows/ci.yml
├── evalsets/
│   ├── regression_v1.yaml      # 离线回归 15 条
│   ├── capability_v1.yaml      # Live 能力 6 条
│   ├── retrieval_v1.yaml       # 检索 Recall@K / MRR 消融
│   ├── reliability_v1.yaml     # pass^k + 工具故障注入
│   └── manual/runtime_cases.yaml  # 手动 DeepSeek 联调
├── docs/
│   ├── ARCHITECTURE.md
│   ├── EVAL.md
│   └── UPDATE_LOG.md
├── src/quant_agent/
│   ├── engine.py               # QuantEngine 产品入口
│   ├── agents/                 # LangGraph 节点、subgraphs、ReAct
│   ├── evidence/               # RAG、memory、document_signal
│   ├── eval/                   # AgentEvalRunner、graders、judge、retrieval/reliability
│   ├── context/                # Context packer、token budget、manifest
│   ├── runtime/                # RuntimeRunner、trace、tool_adapter、tool_policy
│   ├── compliance/ execution/ observability/
│   └── llm_agent.py            # TradingFunctionCaller 工具实现
├── tests/ fixtures/ scripts/
├── reports/                    # eval 报告（本地生成）
├── demo.py                     # 经典 TradingAgent 回测 demo
├── examples_multi_agent.py     # QuantEngine 在线示例
└── pyproject.toml
```

---

## 6. 主要 API

### 6.1 QuantEngine（多智能体）

需配置 `DEEPSEEK_API_KEY`，或在代码中注入兼容的 chat model。

```python
from quant_agent import QuantEngine

result = QuantEngine().analyze(
    "AAPL",
    task="评估供应链风险并给出策略与仓位建议",
    gate={"max_steps": 12, "expect_report": True},
)
print(result.decision, result.report)
print(result.agents_visited, result.trace_steps)
```

### 6.2 TradingAgent（经典回测）

该入口会下载行情数据。建议配置 `FMP_API_KEY`，或确保 OpenBB / yfinance 数据源在当前网络环境可用。

```python
from quant_agent import TradingAgent, AgentConfig, DataConfig, StrategyConfig, BacktestConfig
import datetime as dt

config = AgentConfig(
    data=DataConfig(symbol="AAPL", start=dt.date(2020, 1, 1)),
    strategy=StrategyConfig(name="mean_reversion"),
    backtest=BacktestConfig(initial_cash=100_000),
)
result = TradingAgent(config).run()
```

### 6.3 Agent 评测

```python
from quant_agent.eval import AgentEvalRunner

report = AgentEvalRunner().run_evalset()  # regression_v1
print(report["scorecard"]["summary"])
```

---

## 7. 环境变量速查

完整列表见 [`.env.example`](.env.example) 与 [`docs/UPDATE_LOG.md`](docs/UPDATE_LOG.md#相关环境变量速查)。

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | 在线分析 / Live eval 必需 |
| `FMP_API_KEY` | OpenBB 行情（推荐，避免 Yahoo 限流） |
| `EVIDENCE_FETCH_SEC` | SEC 披露拉取（默认 1；单测/CI eval 自动关） |
| `EVIDENCE_SEARCH_MODE` | `tfidf` / `hybrid` / `embedding` |
| `LANGGRAPH_CHECKPOINT` | `sqlite` / `memory` / `none` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | 可选 trace 上报；需 `pip install langfuse` |
| `AGENT_CONTEXT_BUDGET` | ReAct 上下文 token 预算（默认 8000） |

---

## 8. 其他脚本

| 命令 | 说明 |
|------|------|
| `python demo.py` | 经典规则 Agent 回测；需要可用行情数据源 |
| `python scripts/run_agent.py --symbol AAPL` | 单策略 CLI 回测；需要可用行情数据源 |
| `python scripts/tune_agent.py` | 网格搜索调参；需要可用行情数据源 |
| `python scripts/run_eval.py` | Agent 离线/Live 回归评测 |
| `python scripts/run_retrieval_eval.py` | 检索 Recall@K / MRR 消融 |
| `python scripts/run_reliability_eval.py` | pass^k 稳定性 + 工具故障注入 |
| `python scripts/run_runtime_agent.py` | 手动 DeepSeek 联调 |

---

## 9. 技术栈

Python 3.11+ · pandas · numpy · LangGraph · LangChain-OpenAI（DeepSeek 兼容）· OpenBB / yfinance · scikit-learn · pydantic · pytest · Streamlit（UI，可通过 `.[ui]` 安装）

可选能力：

- Embedding 后端：`pip install -e ".[embedding]"`
- Langfuse trace 上报：`pip install langfuse` 后配置 `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`

---

## 10. 贡献与许可

欢迎 Issue / PR。MIT License，详见 `LICENSE`。

**作者**：Torrie Li · [GitHub](https://github.com/Torrieee)

如果这个项目对你有帮助，请给个 Star。
