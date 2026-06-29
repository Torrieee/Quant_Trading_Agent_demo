# Web 控制台测试指南

启动：

```powershell
cd Quant_Trading_Agent_demo
pip install -e ".[ui]"
python scripts/run_dashboard.py
```

浏览器访问 **http://localhost:8501**

---

## 页面一：分析工作台

### 基础 E2E（Demo，无需 API Key）

1. 左侧 **Demo 模式** 保持开启  
2. 标的：`FIXTURE`  
3. 任务预设：**震荡市策略**  
4. 点击 **开始分析**  
5. 查看 **结论**、**Trace 时间线**（应有 analysis_panel → document_retrieval → research → risk → reporter）

### 动态 Research 子图

1. 勾选 **动态 Research 子图**（或选预设「供应链风险」）  
2. 标的 `FIXTURE`，开始分析  
3. **Trace** 中应出现 `research_planner`、`research_evidence`、`research_verifier`；若并行阶段需要补市场状态，也会出现 `research_market`  
4. **Research / Context** 页签查看 `research_findings`

### Context Engineering

1. 将 **Context token 预算** 调小（如 3000）  
2. 跑分析后打开 **Research / Context** → `context_manifest`（`dropped_items` 可能 > 0）

### Memory 写入

1. 用相同标的/任务连续跑 **两次**  
2. 第二次 **Research / Context** → `memory_lifecycle.last_write_skipped` 可能为 `true`  
3. 或到 **记忆与上下文** 页查看 `memory_meta.json` 记录

### HITL 人工审批

1. 勾选 **HITL（Risk 前人工审批）**  
2. 开始分析 → 页面提示中断  
3. 点击 **批准继续** 或 **拒绝**  
4. 批准后应生成完整报告

### 在线 DeepSeek

1. `.env` 配置 `DEEPSEEK_API_KEY`  
2. 关闭 **Demo 模式**  
3. 标的可用 `AAPL`（会拉行情，需网络）

---

## 页面二：评测中心

| 按钮 | 等价命令 | 验证什么 |
|------|----------|----------|
| E2E 回归 | `python scripts/run_eval.py` | 15 条全链路 case |
| 检索评测 | `python scripts/run_retrieval_eval.py` | RAG Recall@5 / MRR |
| 可靠性评测 | `python scripts/run_reliability_eval.py` | 工具 timeout retry + 不可信文档注入 |
| 运行全部 | 三项离线评测（不含 `pytest`） | 一键回归 |

失败时展开页面错误信息，或查看 `reports/` 下 JSON。

---

## 页面三：记忆与上下文

1. 标的 `FIXTURE` → **加载 Memory 元数据**  
2. 查看 episodic / semantic / `contradicted` 状态  
3. query 填 `supply chain risk` → **执行检索** 验证 RAG 排序

建议先在本页 **分析工作台** 跑 1～2 次分析再加载，否则 meta 可能为空。

---

## 页面四：Trace 洞察

1. 点击 **扫描 trace 目录** → 读取 `data_cache/traces/` 并生成失败 tag 聚类  
2. 点击 **生成 Showcase trace** → 跑 `timeout → retry → replan → HITL → resume` 演示链路  
3. 查看 `reports/trace_insights.json` / `reports/trace_insights.md`

---

## 功能对照表

| 项目能力 | 在控制台怎么测 |
|----------|----------------|
| LangGraph 编排 | 分析工作台 Trace |
| ReAct | 关闭动态 Research，看 research 调工具 |
| 动态 Research | 开启动态子图 + 供应链任务 |
| RAG | 记忆页检索 + 回归「检索评测」 |
| Memory 生命周期 | 重复分析 + 记忆页 meta |
| Context packer | 调小 token 预算看 manifest |
| Agent Eval | 评测中心 |
| Reliability | 评测中心「可靠性评测」 |
| HITL | 分析工作台 HITL 开关 |
| Trace 分析 | Trace 洞察页 |
