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
 (规则节点)      (检索节点)      (Agent)   (Agent + 规则否决)
                     │                │
                     ▼                ▼
              EvidenceRetriever   TradingFunctionCaller
              (ingest/store/      (llm_agent 工具)
               memory/RAG)
```

**定位**：这是一个 **Agentic Workflow**（固定拓扑 + 受约束路由 + 局部自主 Agent），不是「每个节点都是独立 LLM Agent」的多智能体系统。

| 节点 | 类型 | 是否 LLM 自主 |
|------|------|----------------|
| `supervisor` | 代码路由 | 否 — `_choose_next()` 纯规则 |
| `analysis_panel` | 规则信号聚合 | 否 |
| `document_retrieval` | RAG 预检索 | 否 |
| `research` | ReAct 或动态子图 | 是（ReAct 路径） |
| `reflection` | 规则检查 | 否 |
| `risk` | ReAct + 硬否决 | 是（ReAct 路径） |
| `reporter` | 报告生成 | 通常一次 LLM 调用 |

**两套循环，勿混淆：**

| | TradingAgent | QuantEngine + LangGraph |
|---|--------------|-------------------------|
| 定位 | 经典量化回测 pipeline | Agentic 投资分析产品 |
| 入口 | `TradingAgent.run()` | `QuantEngine.analyze()` |
| LLM | 可选 Function Calling | Research / Risk / Reporter 默认 DeepSeek |

**评测入口**：`scripts/run_eval.py`（离线回归 + 可选 Live 能力评测）。

---

## 2. LangGraph 工作流与 Supervisor

### 2.1 固定拓扑、受约束路由

外层是 **预设代码路径** 的工作流：允许的状态转移全部由 `supervisor.py` 的 `_choose_next()` 定义，**不由 LLM 决定下一跳**。

典型顺序：

1. `analysis_panel` → 2. `document_retrieval` → 3. `research` → 4.（可选）`reflection` → 5. `risk` → 6. `reporter`

每个业务节点完成后 **回到 Supervisor**，由代码根据 `WorkflowState` 标志位选择下一节点，例如：

- `analysis_complete` / `retrieval_complete` / `research_complete`
- `workflow_flags.enable_reflection` 决定是否走 `reflection`
- `risk_verdict == reject` 或 `human_approval == reject` 时结束
- `gate.require_human_approval` 时编译图加入 Risk 前静态中断

**为什么每步回 Supervisor？** 统一处理阶段推进、可选 Reflection、Risk 拒绝终止、HITL 中断点，而不是为了「LLM 动态路由」。

### 2.2 节点职责

1. **analysis_panel** — 基本面 / 情绪 / 量化研究规则智能体，输出 `preliminary_decision`
2. **document_retrieval** — 构建证据索引、预检索、`document_signal` 修正决策
3. **research** — 默认 ReAct；`enable_dynamic_research` 时走子图（见 §2.3）
4. **reflection**（可选）— 规则检查研究产出完整性
5. **risk** — ReAct + 规则硬否决（仓位上限、going concern 等）
6. **reporter** — 生成 Markdown 报告

**状态**：`agents/state.py` 中的 `WorkflowState`（含 `quant_state`、`trace_steps`、`gate` 等）。

### 2.3 动态 Research 子图（当前实现边界）

`enable_dynamic_research` 时，`research` 节点 invoke 子图：

```
Planner → Workers → Verifier → [Replan bump → Planner] → Synthesizer
```

**已实现**

- 规则 Planner 输出结构化 `research_plan`（含 `task_id`）
- **market + evidence** 经 LangGraph `Send` **并行**执行；`research_workers_join` 汇合
- **strategy** 在 join 后顺序执行（依赖并行阶段合并后的 `quant_state`）
- Reducer：`merge_findings`（task_id 去重）、`merge_quant_dict`、`operator.add`（trace / step_count）
- 规则 Verifier；失败时 `replan_count` +1，最多 `max_replan`（默认 1）次
- Synthesizer 合并 `research_findings` 写入 `quant_state`

**尚未实现**

- LangGraph 并行 Worker 与 map-reduce state 合并
- 动态 Worker 数量、依赖调度、跨 Worker 去重
- 基于 LLM 的 Planner / Verifier（当前为规则，保证 Demo / CI 可离线跑）

### 2.4 预算与终止

| 限制 | 来源 | 含义 |
|------|------|------|
| `gate.max_steps` | WorkflowState | 图级步数上限 |
| `max_research_steps` / `max_risk_steps` | ReAct 循环 | LLM+工具调用次数 |
| `max_replan` | 动态 Research | Verifier 失败后重规划上限 |
| `ToolExecutionPolicy.max_retries` | tool_adapter | 单次工具超时/失败重试 |

终止优先级（简）：任务完成 → 硬预算耗尽 → Risk 拒绝 / HITL 拒绝 → 连续失败。

### 2.5 HITL 与 Checkpoint

**当前 Demo**：`interrupt_before=["risk"]` + SQLite/Memory checkpointer + `QuantEngine.resume()`。

- 属于 LangGraph **静态断点**，适合快速验证 checkpoint / resume
- 恢复时通过 `update_state` 写入 `human_approval`，再 `invoke(None)` 继续

**生产演进**：独立 `approval_node`，在节点内调用动态 `interrupt()`，返回 `approve / reject / edited_state`。注意：动态 `interrupt()` 恢复后 **节点从头重跑**，中断前副作用须幂等。

实现：`agents/checkpoint.py`、`agents/coordinator.py`、`engine.py`。

---

## 3. Evidence 层

| 组件 | 路径 | 职责 |
|------|------|------|
| Ingest | `evidence/ingest.py` | profile、seed、SEC、新闻 |
| Store | `evidence/store.py` | `HybridEvidenceIndex`（TF-IDF + embedding） |
| Retriever | `evidence/retriever.py` | `ensure_index`、`get_snapshot`、episodic ingest |
| Memory | `evidence/memory.py` | episodic chunk 构建与 merge |
| Memory lifecycle | `evidence/memory_lifecycle.py` | 写入决策、冲突、consolidation |
| Semantic | `evidence/semantic_memory.py` | 规则抽取的长期事实 |
| Document signal | `evidence/document_signal.py` | 披露风险 → 修正 `preliminary_decision` |

**检索模式**（`EVIDENCE_SEARCH_MODE`）：`tfidf` / `hybrid` / `embedding`。

**Episodic Memory**：每次成功 `analyze` 后写入 `data_cache/evidence/{SYMBOL}.json`，下次分析可被检索引用。当前披露证据优先于陈旧 episodic 结论，由 `document_signal` 与 regression case `mem_current_evidence_over_prior` 覆盖。

---

## 4. Context Engineering

`context/pack_workflow_context()` 在 ReAct 前将 `quant_state` 打包为带预算的结构化上下文，并输出 `context_manifest`（可观测，非 LLM 控制）。

规则：字段优先级、来源配额、去重、字符截断。默认预算下多数 case 不触发裁剪；压预算可验证 `dropped_items`。

---

## 5. 工具层

`llm_agent.TradingFunctionCaller` 注册 OpenAI 风格 function schema，经 `runtime/tool_adapter.HarnessToolAdapter` 供 ReAct 循环调用。

主要工具：

- `get_strategy_recommendation` / `analyze_market_state`
- `search_evidence`
- `calculate_position_size`
- `run_backtest`
- `submit_paper_order` / `get_paper_portfolio`

工具返回内容视为 **不可信数据**；`reliability_v1` 含 prompt-injection 样例，断言不调用越权工具。

---

## 6. 可观测与合规

- **Trace**：`observability/tracer.py` → `data_cache/traces/` 或 `AGENT_TRACE_DIR`
- **审计**：`compliance/audit_log.py` → `data_cache/audit/decisions.jsonl`
- **Guardrails**：`compliance/guardrails.py` 对决策做措辞/字段校验

---

## 7. 评测分层（与架构对应）

| 层 | Evalset | 证明什么 |
|----|---------|----------|
| 单元 / 图 | `pytest` + `regression_v1` | reducer、router、adapter、guardrail、状态传递 |
| Fake Model 回归 | `regression_v1` | orchestration / runtime / control plane |
| 检索 | `retrieval_v1` | RAG 召回与 MRR |
| Fake 可靠性 | `reliability_v1` | 工具 timeout 重试、恶意文档不劫持工具 |
| Live | `capability_v1` | 真实模型的工具选择、报告质量、Judge |

---

## 8. 目录映射

```
src/quant_agent/
├── engine.py              # 产品门面
├── agents/
│   ├── coordinator.py     # LangGraph 编译与 run/resume/stream
│   ├── react_loop.py      # Research/Risk 共用 ReAct
│   ├── nodes/             # 各工作流节点
│   ├── subgraphs/         # 动态 Research 子图
│   ├── checkpoint.py
│   └── model_router.py    # 按角色选 DeepSeek 模型
├── evidence/              # RAG + memory
├── context/               # Context packer、token budget、manifest
├── eval/                  # Agent 评测
├── runtime/               # RuntimeRunner、trace、tool_adapter
├── execution/             # 模拟盘
├── compliance/
└── ui/                    # Streamlit
```

---

## 9. 约束（长期）

- 编排：**LangGraph** 固定拓扑；Research / Risk：**ReAct**
- 披露：**US / SEC** 为主，暂不做 A 股
- 代码注释偏好中文
- 产品入口统一 `QuantEngine`，评测统一 `AgentEvalRunner`
