# GitHub 部署快速指南

## 🚀 5 分钟快速部署

### 1. 运行检查脚本（可选）

```powershell
.\check_git_status.ps1
```

### 2. 初始化并推送（如果还没有 Git 仓库）

```powershell
# 初始化
git init

# 添加文件
git add .

# 提交
git commit -m "Initial commit: Quant Trading Agent"

# 添加远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/quant-trading-agent.git

# 推送
git branch -M main
git push -u origin main
```

### 3. 如果已有 Git 仓库

```powershell
# 检查状态
git status

# 添加并提交
git add .
git commit -m "Prepare for GitHub deployment"

# 推送
git push
```

## 📋 文件清单

### ✅ 会上传的文件
- `src/quant_agent/*.py` - 所有源代码
- `scripts/*.py` - CLI 工具
- `*.py` - Demo 和示例脚本
- `*.md` - 所有文档
- `requirements.txt`, `pyproject.toml`, `LICENSE` - 配置文件

### ❌ 不会上传的文件（已在 .gitignore）
- `quant_agent/` - 虚拟环境
- `data_cache/` - 数据缓存
- `__pycache__/` - Python 缓存
- `*.csv` - 数据文件

## 🔐 认证

推送时如果要求认证：
- **用户名**: 你的 GitHub 用户名
- **密码**: Personal Access Token（不是 GitHub 密码）

获取 Token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

## 📝 后续更新

```powershell
git add .
git commit -m "描述你的修改"
git push
```

## 📖 详细指南

查看 `GITHUB_DEPLOYMENT_GUIDE_CN.md` 获取完整指南。

