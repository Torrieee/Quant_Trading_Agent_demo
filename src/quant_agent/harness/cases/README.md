# Harness 用例集

供 `scripts/run_harness.py` / `run_pilot_benchmark.py` 使用，侧重 **工具契约、pilot 编排、回测 trace**，与产品 E2E 评测分离。

| 文件 | 用途 |
|------|------|
| `backtest_cases.yaml` | 回测结果 / 流程质量 |
| `tool_chain_cases.yaml` | 多工具链路与 evidence |
| `llm_tool_cases.yaml` | LLM 工具参数边界 |
| `pilot_tasks.yaml` | 4 条 pilot offline benchmark |
| `runtime_cases.yaml` | 手动 DeepSeek 联调（非 CI eval） |

**QuantEngine E2E 评测** → [`evalsets/`](../../../../evalsets/README.md) + [`docs/EVAL.md`](../../../../docs/EVAL.md)
