# Evalsets

Agent 评测用例集，由 `scripts/run_eval.py` / `AgentEvalRunner` 加载。

| 文件 | 模式 | CI |
|------|------|-----|
| `regression_v1.yaml` | offline（假模型） | 每次 PR，`quality` job |
| `capability_v1.yaml` | live（DeepSeek） | `eval-live` job（需 secret） |

完整说明见 [`docs/EVAL.md`](../docs/EVAL.md)。
