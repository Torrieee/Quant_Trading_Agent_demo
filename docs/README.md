# 文档索引

| 文档 | 内容 |
|------|------|
| [SHOWCASE_TRACE.md](SHOWCASE_TRACE.md) | 韧性演示 trace + Trace 分析 |
| [UI_GUIDE.md](UI_GUIDE.md) | Streamlit 控制台测试步骤 |
| [../README.md](../README.md) | 项目总览、快速开始、CI、命令速查 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Agentic Workflow 架构、数据流、模块职责 |
| [EVAL.md](EVAL.md) | Agent 评测框架：数据集、graders、CI、Live |
| [UPDATE_LOG.md](UPDATE_LOG.md) | 版本演进与选型记录（最新在前） |

## 报告产物（本地 / CI artifact）

| 路径 | 说明 |
|------|------|
| `reports/eval_regression_v1.json` | 离线回归 scorecard |
| `reports/eval_capability_v1.json` | Live 能力评测 scorecard |
| `reports/eval_retrieval_v1.json` | 检索 Recall@K / MRR 消融 |
| `reports/eval_reliability_v1.json` | 可靠性评测（故障恢复 + 不可信文档注入） |
| `reports/traces/` | eval 运行时 trace（`scripts/run_eval.py --trace`） |
| `data_cache/traces/` | 产品 trace 与 showcase trace（可由 `AGENT_TRACE_DIR` 覆盖） |
| `data_cache/evidence/` | Episodic / 索引持久化 |
| `data_cache/audit/decisions.jsonl` | 合规审计日志 |
