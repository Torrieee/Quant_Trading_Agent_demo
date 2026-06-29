# Agent 评测框架

评测对象：**`QuantEngine.analyze()` 全链路**（非 Harness Planner 路径）。

## 1. 两层 Evalset

| 文件 | `model` | 条数 | 用途 |
|------|---------|------|------|
| `evalsets/regression_v1.yaml` | `fake` | 11 | CI 阻断：确定性、无 API 费用 |
| `evalsets/capability_v1.yaml` | `live` | 6 | 真实 DeepSeek 能力评估 + 可选 Judge |

### 离线回归（regression_v1）

- **环境**：`FIXTURE` + `tests/fixtures/sample_ohlcv.csv` + 内置 seed 文档
- **模型**：`eval/fake_model.py` 的 `RoleAwareFakeModel`
- **隔离**：每次 run 使用独立 `EVIDENCE_STORE_DIR`，关闭 SEC/新闻网络
- **期望**：code grader（节点到达、字段存在、risk_flags、工具调用等）

能力域覆盖：`orchestration` · `tool` · `evidence` · `memory` · `safety` · `hitl`

### Live 能力（capability_v1）

- **环境**：FIXTURE / AAPL + fixture K 线（不依赖 yfinance）
- **模型**：真 DeepSeek（`DEEPSEEK_API_KEY`）
- **门槛**：`min_pass_rate: 0.67`（6 条至少 4 条 code pass）
- **Judge**：DeepSeek LLM-as-Judge 打分（默认 `require_judge: false`，仅记录不阻断）

---

## 2. 一条 Case 的结构

```yaml
- name: rag_supply_chain_flags
  tags: [evidence]
  symbol: FIXTURE
  fixture: sample_ohlcv.csv
  task: "评估 FIXTURE 的供应链风险..."
  gate:
    max_steps: 12
    expected_agents: [analysis_panel, document_retrieval, research, risk, reporter]
    expect_report: true
  setup:                    # 可选：预置 episodic / extra_docs
    episodic: [...]
  expect:                   # code grader 断言
    risk_flags_contains: [supply_chain]
    document_signal_applied: true
  judge: true               # Live：是否跑 LLM Judge
```

**三层含义：**

1. **环境层** — symbol、fixture、setup、eval 隔离 env  
2. **任务层** — `task`、`gate`、`workflow_flags`  
3. **期望层** — `expect`（code）+ 可选 Judge  

---

## 3. 运行命令

```bash
# 离线回归（默认，CI 同款）
python scripts/run_eval.py
python scripts/run_eval.py --evalset evalsets/regression_v1.yaml --output reports/eval_regression_v1.json

# Live 能力评测
export DEEPSEEK_API_KEY=sk-...
python scripts/run_eval.py --live --judge

# 关闭 Judge
python scripts/run_eval.py --live --no-judge

# 写入 trace
python scripts/run_eval.py --trace
```

**Python API：**

```python
from quant_agent.eval import AgentEvalRunner

report = AgentEvalRunner().run_evalset()
print(report["scorecard"])
print(report["benchmark"])      # 门槛检查结果
print(report["judge_summary"])  # Live Judge 汇总
```

---

## 4. Grader 类型

| 类型 | 模块 | 说明 |
|------|------|------|
| Runtime gate | `runtime/runner.py` | 节点、report、position_size、风控 |
| Evidence coverage | `eval/evidence_coverage.py` | `required_evidence_keys` |
| Expect | `eval/graders.py` | risk_flags、document_signal、required_tools 等 |
| LLM Judge | `eval/judge.py` | tool_selection、evidence_sufficiency、efficiency、answer_grounding（1–5） |
| Benchmark | `eval/benchmark.py` | evalset 级 `min_pass_rate` |

**Failure taxonomy**：`eval/taxonomy.py` 将 failures 映射为 `orchestration_skip`、`evidence_miss` 等 tag。

---

## 5. CI 集成

`.github/workflows/ci.yml`：

| Job | 命令 | 条件 |
|-----|------|------|
| `quality` | `python scripts/run_eval.py` | 每次 PR/push，**必须全绿** |
| `eval-live` | `python scripts/run_eval.py --live --judge` | 需 `DEEPSEEK_API_KEY` secret；无则 skip |

Artifacts：`eval-regression-v1`、`eval-capability-v1`（JSON + Markdown）。

**配置 Secret：** GitHub → Settings → Secrets → Actions → `DEEPSEEK_API_KEY`

---

## 6. 扩展 Evalset

1. 在 `evalsets/` 新增 YAML，或向现有文件追加 case  
2. 每条 case 标明 `tags`（能力域）和 `expect`  
3. 离线 case 必须用 `model: fake` + FIXTURE，保证确定性  
4. Live case 避免 `required_tools` 等强轨迹断言（LLM 路径不固定）  
5. 跑通后更新 `benchmark.min_pass_rate`  

---

## 7. 手动联调

DeepSeek 在线联调用例见 `evalsets/manual/runtime_cases.yaml`，执行：

```bash
python scripts/run_runtime_agent.py --cases evalsets/manual/runtime_cases.yaml
```
