# 文档索引

| 文档 | 内容 |
|------|------|
| [../README.md](../README.md) | 项目总览、快速开始、CI、命令速查 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 多智能体架构、数据流、模块职责 |
| [EVAL.md](EVAL.md) | Agent 评测框架：数据集、graders、CI、Live |
| [UPDATE_LOG.md](UPDATE_LOG.md) | 版本演进与选型记录（最新在前） |

## 报告产物（本地 / CI artifact）

| 路径 | 说明 |
|------|------|
| `reports/eval_regression_v1.json` | 离线回归 scorecard |
| `reports/eval_capability_v1.json` | Live 能力评测 scorecard |
| `reports/traces/` | 运行时 trace（可选 `--trace`） |
| `data_cache/evidence/` | Episodic / 索引持久化 |
| `data_cache/audit/decisions.jsonl` | 合规审计日志 |
