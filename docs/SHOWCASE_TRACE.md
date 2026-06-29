# Showcase Trace：韧性全链路演示

用于项目演示讲解：**timeout → retry → verifier fail → replan → HITL → resume**

## 生成

```powershell
cd Quant_Trading_Agent_demo-main
python scripts/run_showcase_trace.py
```

输出：

- `data_cache/traces/showcase_resilience_FIXTURE_<timestamp>.json`
- `reports/showcase_resilience_summary.json`
- `reports/trace_insights.json`（自动刷新聚类）

或在 Streamlit **Trace 洞察** 页点击「生成 Showcase trace」。

## 口述时间线

1. Supervisor 进入 Research（动态子图）
2. Planner 生成 market + evidence 并行任务
3. LangGraph **Send** 并行执行 `research_market` / `research_evidence`
4. strategy 工具首次 **timeout** → ToolPolicy **retry** 成功
5. Verifier 首次失败（`gate.force_research_replan_once`）→ **replan**
6. 第二次 Planner → Workers → Verifier 通过
7. Risk 前 **HITL interrupt**
8. `resume(human_approval=pass)` → Reporter 完成报告

## 在线 Trace 分析

```powershell
python scripts/run_trace_analysis.py
```

读取 `data_cache/traces/`，输出：

- 失败 **tag 聚类**（`eval/taxonomy.py`）
- 事件统计（`tool_retry`、`verifier_fail`、`parallel_worker`…）
- **闭环建议**（写入 `reports/trace_insights.md`）

Eval 失败时 `AgentEvalRunner` 会自动 `ingest_eval_failure` 写入轻量 trace，纳入聚类。

## 并行 Research 说明

- **market + evidence**：LangGraph `Send` 并行，经 `research_workers_join` 汇合
- **strategy**：join 后顺序执行（依赖并行阶段的 `quant_state`）
- State reducer：`merge_findings`（按 `task_id` 去重）、`merge_quant_dict`、`operator.add` trace

详见 `docs/ARCHITECTURE.md` §2.3。
