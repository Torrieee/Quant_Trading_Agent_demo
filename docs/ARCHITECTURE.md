# 架构说明

## 1. 总览

```
用户 / Dashboard / YAML Eval Case
           │
           ▼
    QuantEngine.analyze()
           │
           ▼
    AgentCoordinator (LangGraph)
           │
     ┌─────┴─────┬──────────────┬─────────┐
     ▼           ▼              ▼         ▼
analysis_panel  document_retrieval  research  risk → reporter
 (规则信号)      (RAG 预检索)      (ReAct)   (ReAct + 规则否决)
                     │                │
                     ▼                ▼
              EvidenceRetriever   TradingFunctionCaller
              (ingest/store/      (llm_agent 工具)
               memory/RAG)
```

**两套循环，勿混淆：**

| | TradingAgent | QuantEngine + LangGraph |
|---|--------------|-------------------------|
| 定位 | 经典量化回测 pipeline | 多智能体投资分析产品 |
| 入口 | `TradingAgent.run()` | `QuantEngine.analyze()` |
| LLM | 可选 Function Calling | Research / Risk / Reporter 默认 DeepSeek |

**评测入口**：`scripts/run_eval.py`（离线回归 + 可选 Live 能力评测）。

## 2. LangGraph 工作流

**节点顺序（经 Supervisor 路由）：**

1. **analysis_panel** — 基本面 / 情绪 / 量化研究规则智能体，输出 `preliminary_decision`
2. **document_retrieval** — 构建证据索引、预检索、`document_signal` 修正决策
3. **research** — DeepSeek ReAct：`search_evidence`、`get_strategy_recommendation` 等
4. **reflection**（可选，`workflow_flags.enable_reflection`）— 对研究结论做自检
5. **risk** — ReAct 调用 `calculate_position_size` + `evaluate_risk_rules` 硬否决
6. **reporter** — 生成 Markdown 报告

**状态**：`agents/state.py` 中的 `WorkflowState`（含 `quant_state`、`trace_steps`、`gate` 等）。

**Checkpoint**：`agents/checkpoint.py`；HITL 在 `risk` 前 `interrupt_before`，通过 `QuantEngine.resume()` 继续。

---

## 3. Evidence 层

| 组件 | 路径 | 职责 |
|------|------|------|
| Ingest | `evidence/ingest.py` | profile、seed、SEC、新闻 |
| Store | `evidence/store.py` | `HybridEvidenceIndex`（TF-IDF + embedding） |
| Retriever | `evidence/retriever.py` | `ensure_index`、`get_snapshot`、episodic ingest |
| Memory | `evidence/memory.py` | episodic chunk 构建与 merge |
| Semantic | `evidence/semantic_memory.py` | 规则抽取的长期事实 |
| Document signal | `evidence/document_signal.py` | 披露风险 → 修正 `preliminary_decision` |

**检索模式**（`EVIDENCE_SEARCH_MODE`）：`tfidf` / `hybrid` / `embedding`。

**Episodic Memory**：每次成功 `analyze` 后写入 `data_cache/evidence/{SYMBOL}.json`，下次分析可被检索引用。

---

## 4. 工具层

`llm_agent.TradingFunctionCaller` 注册 OpenAI 风格 function schema，经 `runtime/tool_adapter.HarnessToolAdapter` 供 ReAct 循环调用。

主要工具：

- `get_strategy_recommendation` / `analyze_market_state`
- `search_evidence`
- `calculate_position_size`
- `run_backtest`
- `submit_paper_order` / `get_paper_portfolio`

---

## 5. 可观测与合规

- **Trace**：`observability/tracer.py` → `data_cache/traces/` 或 `AGENT_TRACE_DIR`
- **审计**：`compliance/audit_log.py` → `data_cache/audit/decisions.jsonl`
- **Guardrails**：`compliance/guardrails.py` 对决策做措辞/字段校验

---

## 6. 目录映射

```
src/quant_agent/
├── engine.py              # 产品门面
├── agents/
│   ├── coordinator.py     # LangGraph 编译与 run/resume/stream
│   ├── react_loop.py      # Research/Risk 共用 ReAct
│   ├── nodes/             # 各智能体节点
│   ├── checkpoint.py
│   └── model_router.py    # 按角色选 DeepSeek 模型
├── evidence/              # RAG + memory
├── eval/                  # Agent 评测
├── runtime/               # RuntimeRunner、trace、tool_adapter
├── execution/             # 模拟盘
├── compliance/
└── ui/                    # Streamlit
```

---

## 7. 约束（长期）

- 编排：**LangGraph**；Research / Risk：**ReAct**
- 披露：**US / SEC** 为主，暂不做 A 股
- 代码注释偏好中文
- 产品入口统一 `QuantEngine`，评测统一 `AgentEvalRunner`
