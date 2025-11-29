# GitHub 部署指南

## 📋 部署前检查清单

### ✅ 确保以下文件存在

- [x] `README.md` - 项目说明（已更新）
- [x] `LICENSE` - 许可证文件（MIT License）
- [x] `.gitignore` - Git 忽略文件（已创建）
- [x] `requirements.txt` - 依赖列表
- [x] `pyproject.toml` - 项目配置
- [x] `PROJECT_DESCRIPTION.md` - 项目详细说明
- [x] `RESUME_GUIDE.md` - 简历指南

### ✅ 确保以下内容被忽略（已在 .gitignore 中）

- [x] `__pycache__/` - Python 缓存
- [x] `data_cache/` - 数据缓存
- [x] `.venv/` - 虚拟环境
- [x] `*.egg-info/` - 打包信息
- [x] `*.pyc` - Python 编译文件

## 🚀 部署步骤

### 步骤 1：在 GitHub 上创建仓库

1. 登录 GitHub
2. 点击右上角 **"+"** → **"New repository"**
3. 填写信息：
   - **Repository name**: `quant-trading-agent`（或你喜欢的名字）
   - **Description**: `A quantitative trading agent framework with backtesting and parameter optimization`
   - **Visibility**: 选择 **Public**（公开）或 **Private**（私有）
   - ⚠️ **不要勾选** "Initialize this repository with a README"（我们已有 README）
4. 点击 **"Create repository"**

### 步骤 2：在本地初始化 Git 并推送

在项目根目录（`E:\Desktop\quant_agent`）打开 PowerShell 或终端，执行：

```powershell
# 1. 初始化 Git 仓库
git init

# 2. 添加所有文件（.gitignore 会自动排除不需要的文件）
git add .

# 3. 提交到本地仓库
git commit -m "Initial commit: Quant Trading Agent project

- Implemented TradingAgent class with perceive-decide-act-evaluate cycle
- Added data fetching module supporting multiple markets
- Implemented mean reversion and momentum strategies
- Built backtesting engine with comprehensive metrics
- Added automatic parameter optimization with grid search
- Created CLI tools and demo scripts"

# 4. 添加远程仓库（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/quant-trading-agent.git

# 5. 重命名主分支为 main
git branch -M main

# 6. 推送到 GitHub
git push -u origin main
```

### 步骤 3：处理认证问题

如果推送时要求输入用户名和密码：

#### 方法 1：使用 Personal Access Token（推荐）

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. 点击 **"Generate new token (classic)"**
3. 填写信息：
   - **Note**: `quant-agent-deployment`
   - **Expiration**: 选择合适的时间（如 90 天）
   - **Select scopes**: 勾选 `repo`（完整仓库访问权限）
4. 点击 **"Generate token"**
5. **复制 token**（只显示一次，务必保存）
6. 推送时：
   - **Username**: 你的 GitHub 用户名
   - **Password**: 粘贴刚才复制的 token

#### 方法 2：使用 SSH（可选）

如果你已经配置了 SSH 密钥：

```powershell
# 使用 SSH URL
git remote set-url origin git@github.com:YOUR_USERNAME/quant-trading-agent.git
git push -u origin main
```

### 步骤 4：优化 GitHub 仓库

#### 4.1 添加 Topics（标签）

在仓库页面点击 **"Add topics"**，添加：
- `quantitative-trading`
- `python`
- `backtesting`
- `trading-strategy`
- `finance`
- `agent`
- `machine-learning`（如果适用）

#### 4.2 添加仓库描述

在仓库设置中更新描述：
```
A quantitative trading agent framework with backtesting and parameter optimization. Implements TradingAgent class with perceive-decide-act-evaluate cycle.
```

#### 4.3 添加 README 徽章（可选）

README 中已包含徽章，如果需要更多，可以访问 [shields.io](https://shields.io/)

## 📝 后续更新代码

### 日常更新流程

```powershell
# 1. 查看修改状态
git status

# 2. 添加修改的文件
git add .

# 3. 提交修改（写清楚修改内容）
git commit -m "Add feature: 描述你的修改"

# 4. 推送到 GitHub
git push
```

### 提交信息规范

推荐使用清晰的提交信息：

```powershell
# 功能添加
git commit -m "Add feature: support for cryptocurrency data"

# Bug 修复
git commit -m "Fix: resolve MultiIndex column handling issue"

# 文档更新
git commit -m "Docs: update README with deployment guide"

# 代码重构
git commit -m "Refactor: improve agent class structure"
```

## 🔍 验证部署

部署完成后，检查：

1. ✅ 仓库可以正常访问
2. ✅ README 显示正常
3. ✅ 所有文件都已上传
4. ✅ 代码可以正常查看
5. ✅ LICENSE 文件显示

## 🎨 可选：添加截图

如果想让项目更吸引人，可以：

1. 运行 demo 生成图片
2. 将图片添加到 `images/` 目录
3. 在 README 中引用图片

```markdown
![Demo Screenshot](images/demo_screenshot.png)
```

## 📊 GitHub 统计

部署后，GitHub 会自动显示：
- ⭐ Star 数量
- 🍴 Fork 数量
- 👁️ Watch 数量
- 📈 贡献图表

## 🔗 在简历中链接

部署完成后，在简历中使用：

```
GitHub: https://github.com/YOUR_USERNAME/quant-trading-agent
```

或者使用短链接（如果 GitHub 用户名较长）。

## ⚠️ 注意事项

1. **不要提交敏感信息**：确保 `.gitignore` 正确配置
2. **不要提交大文件**：数据缓存文件已在 `.gitignore` 中
3. **保持代码质量**：确保代码可以正常运行
4. **完善文档**：README 和代码注释要清晰

## 🆘 常见问题

### Q: 推送时提示 "remote: Permission denied"
A: 检查用户名和 token 是否正确，或者使用 SSH 方式

### Q: 如何删除已提交的文件？
A: 
```powershell
git rm --cached filename
git commit -m "Remove file"
git push
```

### Q: 如何更新远程仓库 URL？
A:
```powershell
git remote set-url origin NEW_URL
```

### Q: 如何查看提交历史？
A:
```powershell
git log --oneline
```

---

**完成部署后，记得更新 README 中的 GitHub 链接！**

