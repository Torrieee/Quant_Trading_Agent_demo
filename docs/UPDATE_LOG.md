# 项目更新记录

本文档记录 **Quant Trading Agent Demo** 的主要演进：每次改了什么、为什么改、以及当时的技术选型理由。  
后续每次有意义的功能/架构变更，请在本文件 **顶部** 追加一条（最新在前）。

---

### 2026-06-29 — 评审反馈对齐：术语、评测语义、Agent eval 扩展

**改了什么**
- README / `ARCHITECTURE.md` / `EVAL.md`：「Agentic Workflow + 代码 Supervisor」替代过度「多智能体」表述；明确节点类型与 HITL 静态中断语义
- `reliability_v1`：主指标改为故障恢复（非 Fake Model `pass^k`）；新增 `reli_untrusted_doc_ignored`
- `graders.py`：`at_least_one_of_tools`、`forbidden_tools`
- `regression_v1` 新增 `mem_current_evidence_over_prior`（15 条）

**为什么改**
- 评审反馈：概念表述须与代码一致；Fake Model 测工作流控制面，Live 测 policy；确定性 pass^k 信息量低

---

### 2026-06-29 — 动态 Research 子图 + Memory 生命周期

**改了什么**
- `agents/subgraphs/`：Planner → Workers → Verifier → Replan → Synthesizer；`workflow_flags.enable_dynamic_research` 启用
- `evidence/memory_lifecycle.py`：写入决策、冲突检测、episodic→semantic consolidation、检索降权
- `regression_v1` 新增 `mem_lifecycle_consolidation`、`mem_skip_duplicate_write`、`research_dynamic_supply_chain`

**为什么改**
- 外层确定性工作流 + 内层动态研究；Memory 从无脑 append 升级为可决策、可合并、可降权

---

### 2026-06-29 — Context Engine + Retrieval/Reliability Eval

**改了什么**
- 新增 `context/`：`pack_workflow_context`、token 预算、来源配额、`context_manifest`；Research/Risk ReAct 改用打包上下文
- 新增 `runtime/tool_policy.py`：超时重试、输出截断、评测用故障注入
- 新增 `eval/retrieval_eval.py`、`eval/reliability.py` 与 `retrieval_v1` / `reliability_v1` evalset
- CI 增加 `run_retrieval_eval.py`、`run_reliability_eval.py`

**为什么改**
- 面向 Agent 能力展示上下文工程、可测量 RAG 与可靠性（故障恢复、故障注入）能力

---

### 2026-06-29 — 移除遗留五层 Harness

**改了什么**
- 删除 `harness/` 五层编排（orchestrator / planner / executor / pilot 等）及 `run_harness.py`、`run_pilot_benchmark.py`
- 将 `tool_adapter`、`trace`、`trace_store` 迁至 `runtime/`；`evidence_coverage`、`efficiency`、`llm_judge` 迁至 `eval/`
- 当时 CI 仅保留 `pytest` + `run_eval.py`；手动联调用例移至 `evalsets/manual/runtime_cases.yaml`
- 删除重复子目录 `QuantTradingAgent/`（与仓库根目录重复）

**为什么改**
- 产品评测统一为 QuantEngine E2E；五层工具链 Harness 与主链路口径重复

---

### 2026-06-29 — Agent 评测框架 + CI 接入

**改了什么**
- 新包 `src/quant_agent/eval/`：`AgentEvalRunner`、`fake_model`、`graders`、`judge`、`benchmark`、`scorecard`、`taxonomy`
- `evalsets/regression_v1.yaml`：11 条离线回归（FIXTURE + 假模型）
- `evalsets/capability_v1.yaml`：6 条 Live 能力评测（真 DeepSeek + 可选 LLM Judge）
- `scripts/run_eval.py`：`--live` / `--judge` / scorecard 输出
- `.github/workflows/ci.yml`：`quality` job 增加 `run_eval.py`；新增 `eval-live` job（需 `DEEPSEEK_API_KEY` secret）
- 文档：`README.md`、`docs/ARCHITECTURE.md`、`docs/EVAL.md`、`docs/README.md`
- 修复：`evidence/memory.py` `merge_chunk_lists` 保留 eval 注入的自定义文档 chunk

**为什么改**
- 需要可复现的 **E2E agent 回归**（CI 阻断）与 **Live 能力评估**（相对门槛，非绝对 100%）
- 评测对象统一为 `QuantEngine`，与旧工具契约评估分离

**怎么做 / 选型**
- 离线层：`RoleAwareFakeModel` + code grader，PR 必跑、零 API 成本
- Live 层：`min_pass_rate: 0.67`；Judge 默认 `require_judge: false`（记分不阻断）
- 当时未把旧 pilot benchmark 并入 eval：口径不同，先并行保留

---

### 2026-06-29 — 前沿 Gap 补齐

**改了什么**
- RAG：`chunking.py` SEC 分段、`query_expand.py`、`rerank.py`、新闻插件 `news_feed.py`
- 决策闭环：`document_signal.py` 修正 `preliminary_decision`
- 记忆：`semantic_memory.py` 分层 semantic facts
- HITL：`interrupt_before=["risk"]` + `QuantEngine.resume()`
- 可观测：`observability/tracer.py` JSON trace + 可选 Langfuse
- 执行：`execution/paper_trading.py` + 工具 `submit_paper_order`
- 合规：`compliance/audit_log.py`、`guardrails.py`
- 编排：可选 `reflection` 节点、`model_router.py` 按角色选模型
- 流式：`QuantEngine.analyze_stream()` / `coordinator.run_stream()`

**为什么改**
- 对齐前沿 agent：证据驱动决策、HITL、执行闭环、审计、语义检索增强

**怎么做 / 选型**
- rerank 默认 lexical overlap，可选 cross-encoder
- semantic memory 规则抽取（无 LLM），与 episodic 并存
- 未引入独立向量库/Chroma

---

```markdown
### YYYY-MM-DD — 标题

**改了什么**
- …

**为什么改**
- …

**怎么做 / 选型**
- …
- 备选方案：…（未选原因）
```

---

### 2026-06-28 — Embedding Hybrid 检索 + LangGraph Checkpoint

**改了什么**
- `evidence/embeddings.py`：Hashing（默认）与 sentence-transformers（可选）向量后端
- `evidence/store.py`：`HybridEvidenceIndex`，支持 `tfidf` / `hybrid` / `embedding` 三种 `EVIDENCE_SEARCH_MODE`
- `agents/checkpoint.py` + `agents/serialization.py`：SQLite/Memory checkpoint；DataFrame / numpy 序列化
- `agents/coordinator.py`：编译图时挂载 checkpointer；`thread_id`；节点 `_checkpoint_safe`
- `engine.py`：支持 `thread_id`、`checkpointer`、`enable_checkpoint`
- 依赖：`langgraph-checkpoint-sqlite`；可选 extra `embedding`

**为什么改**
- 纯 TF-IDF 对「换说法的同一语义问题」召回弱
- 工作流无 checkpoint：中断即重跑，无法按 thread 查状态
- checkpoint 需要 state 可序列化（DataFrame、numpy 会失败）

**怎么做 / 选型**
- **Hybrid** = α×稠密向量 + (1−α)×TF-IDF，再乘 recency / episodic boost；**不是** TF-IDF 与 episodic 的混合
- 默认 embedding 用 sklearn `HashingVectorizer`：零下载、离线、与现有 `scikit-learn` 依赖一致
- 更强语义可选 `pip install "quant-agent[embedding]"` + `EVIDENCE_EMBEDDING_BACKEND=sentence_transformers`
- Checkpoint 默认 **SQLite** 落盘 `data_cache/checkpoints/langgraph.db`；测试用 `memory`
- 未选 Postgres checkpoint：demo 规模 SQLite 足够；未选 Chroma：避免引入独立向量库运维

---

### 2026-06-28 — Episodic Memory 与前沿对齐

**改了什么**
- `evidence/memory.py`：结构化 `build_episodic_chunk`、`merge_chunk_lists`
- `evidence/persistence.py`：按 symbol 的 JSON 持久化 `data_cache/evidence/{SYMBOL}.json`
- `engine.py`：`ingest_episodic_session` 替代 `ingest_analysis_report`
- `document_retrieval` / Research / Reporter prompt 引用 `episodic_memory`
- 测试：`test_episodic_memory.py`；conftest 隔离 evidence 目录

**为什么改**
- 改前：`ensure_index` 全量重建会 **清掉** 上次分析报告；无跨会话记忆
- 前沿 agent 普遍有 **episodic / session memory**，用于对比历次决策

**怎么做 / 选型**
- 每条 analyze 写入一条 `doc_type=episodic_memory` 的 chunk，与 SEC/seed/profile **增量 merge**
- 默认每 symbol 最多 20 条（`EVIDENCE_MAX_EPISODIC`）
- 未选独立向量库存 episodic：与主索引共用 chunk 模型，实现简单
- 未选 LangGraph Store 存 memory：先用 JSON + 同一 retriever，降低耦合

---

### 2026-06-28 — 代码清理（删除旧 runtime / RAG 路径）

**改了什么**
- 删除旧 `runtime/nodes/*`、`RAGSystem`、`LLMTradingAgent`、冗余 examples
- 保留：`runtime/runner.py`（兼容执行器）、`demo.py`、`examples_multi_agent.py`
- 移除未用依赖：`langchain`、`langchain-community`、`faiss-cpu`

**为什么改**
- 双轨架构（旧 runtime vs 新 LangGraph）易混淆、难维护
- 产品入口统一为 `QuantEngine` + `agents/coordinator`

**怎么做 / 选型**
- 只删无引用路径；旧评估环路与产品 analyze 分离保留

---

### 2026-06-28 — SEC 披露默认开启 + 集成测试

**改了什么**
- `evidence/plugins/sec_edgar.py`：10-K/10-Q 拉取；CIK 缓存；重试
- 默认 `EVIDENCE_FETCH_SEC=1`；单元测试 conftest 关闭 SEC 网络
- `scripts/test_sec_evidence.py`、`tests/test_sec_evidence_integration.py`

**为什么改**
- Demo 应对齐美股公开披露数据源（SEC EDGAR）
- 默认关 SEC 时 RAG 只有 seed，演示效果弱

**怎么做 / 选型**
- 在线拉取 + 本地 `data_cache/sec/` 缓存；失败回退 seed
- 未做 AkShare/A 股：用户约束先做 US/SEC

---

### 2026-06-28 — RAG Evidence 层 + document_retrieval 节点

**改了什么**
- 新包 `evidence/`：ingest、store、retriever、document_rules
- LangGraph 增加 `document_retrieval` 节点；`search_evidence` 工具
- 路由：`analysis_panel → document_retrieval → research → risk → reporter`
- TF-IDF 内存索引（初版）

**为什么改**
- 研究/报告需要可引用的披露与基本面文本，而非纯 OHLCV
- 与前沿 quant agent 的 **RAG + 工具** 模式对齐

**怎么做 / 选型**
- **TF-IDF**：零额外模型、实现可控、英文 10-K 关键词匹配尚可
- 未选 FAISS/Chroma 初版：demo 文档量小，避免 embedding 模型与 GPU 依赖
- 未选 BM25 库：手写 TF-IDF 足够，少依赖

---

### 2026-06-28 — 策略推荐 scoring + get_strategy_recommendation 升级

**改了什么**
- `strategy_recommendation.py`：momentum / mean_reversion 打分、confidence、alternatives、risk_flags 降权
- `llm_agent.py` 工具接入；保持 `{market_state: "ranging"}` 向后兼容

**为什么改**
- 原工具仅规则映射，无法体现波动率、趋势强度、证据风险对策略的影响

**怎么做 / 选型**
- 显式 scoring 表 + 可调权重，结果可解释、可单测
- 未让 LLM 直接「拍策略」：保留工具输出结构化，便于评测

---

## 架构约束（长期有效）

- 编排：**LangGraph**；Research / Risk：**ReAct**（`react_loop.py`）
- 产品入口：`QuantEngine.analyze()` → `AgentCoordinator`
- 产品 E2E 评测：`scripts/run_eval.py` + `evalsets/`
- 暂不做 A 股；披露路径以 SEC 为主
- 代码注释偏好中文；不在代码/comments 中引用外部项目名

---

## 相关环境变量速查

| 变量 | 默认 | 含义 |
|------|------|------|
| `DEEPSEEK_API_KEY` | — | 在线分析 / Live eval（CI secret 同名） |
| `DEEPSEEK_MODEL` | deepseek-chat | 主模型 |
| `DEEPSEEK_MODEL_RESEARCH` / `_RISK` / `_REPORTER` | 回退主模型 | 按角色路由 |
| `EVIDENCE_SEARCH_MODE` | hybrid | tfidf / hybrid / embedding |
| `EVIDENCE_HYBRID_ALPHA` | 0.45 | hybrid 中 embedding 权重 |
| `EVIDENCE_EMBEDDING_BACKEND` | hashing | hashing / sentence_transformers |
| `EVIDENCE_STORE_DIR` | data_cache/evidence | Episodic + 索引 JSON |
| `EVIDENCE_MAX_EPISODIC` | 20 | 每 symbol episodic 条数上限 |
| `EVIDENCE_FETCH_SEC` | 1 | SEC 拉取（eval 运行时自动关） |
| `EVIDENCE_FETCH_NEWS` | 1 | 新闻插件 |
| `LANGGRAPH_CHECKPOINT` | sqlite | sqlite / memory / none |
| `LANGGRAPH_CHECKPOINT_DB` | data_cache/checkpoints/langgraph.db | SQLite 路径 |
| `AGENT_TRACE_DIR` | data_cache/traces | 运行 trace 目录 |
| `AUDIT_LOG_PATH` | data_cache/audit/decisions.jsonl | 审计日志 |
