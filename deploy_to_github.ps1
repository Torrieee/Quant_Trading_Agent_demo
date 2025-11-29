# GitHub 部署脚本 (PowerShell)
# 使用方法: .\deploy_to_github.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Quant Trading Agent - GitHub 部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Git 是否已初始化
if (-not (Test-Path .git)) {
    Write-Host "[1/5] 初始化 Git 仓库..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git 仓库已初始化" -ForegroundColor Green
} else {
    Write-Host "[1/5] Git 仓库已存在，跳过初始化" -ForegroundColor Green
}

# 检查是否有未提交的更改
Write-Host ""
Write-Host "[2/5] 检查文件状态..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "发现未提交的文件，准备添加..." -ForegroundColor Yellow
    git add .
    Write-Host "✓ 文件已添加到暂存区" -ForegroundColor Green
} else {
    Write-Host "✓ 没有未提交的更改" -ForegroundColor Green
}

# 检查是否需要提交
$hasCommits = git rev-parse --verify HEAD 2>$null
if (-not $hasCommits -or $status) {
    Write-Host ""
    Write-Host "[3/5] 提交更改..." -ForegroundColor Yellow
    $commitMessage = @"
Initial commit: Quant Trading Agent project

- Implemented TradingAgent class with perceive-decide-act-evaluate cycle
- Added data fetching module supporting multiple markets
- Implemented mean reversion and momentum strategies
- Built backtesting engine with comprehensive metrics
- Added automatic parameter optimization with grid search
- Created CLI tools and demo scripts
"@
    git commit -m $commitMessage
    Write-Host "✓ 更改已提交" -ForegroundColor Green
} else {
    Write-Host "[3/5] 已有提交，跳过" -ForegroundColor Green
}

# 检查远程仓库
Write-Host ""
Write-Host "[4/5] 检查远程仓库配置..." -ForegroundColor Yellow
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host "未配置远程仓库" -ForegroundColor Yellow
    Write-Host ""
    $username = Read-Host "请输入你的 GitHub 用户名"
    $repoName = Read-Host "请输入仓库名称 (默认: quant-trading-agent)"
    if (-not $repoName) {
        $repoName = "quant-trading-agent"
    }
    
    Write-Host ""
    Write-Host "选择认证方式:" -ForegroundColor Yellow
    Write-Host "1. HTTPS (使用 Personal Access Token)"
    Write-Host "2. SSH (需要配置 SSH 密钥)"
    $choice = Read-Host "请选择 (1 或 2)"
    
    if ($choice -eq "2") {
        $remoteUrl = "git@github.com:$username/$repoName.git"
    } else {
        $remoteUrl = "https://github.com/$username/$repoName.git"
    }
    
    git remote add origin $remoteUrl
    Write-Host "✓ 远程仓库已配置: $remoteUrl" -ForegroundColor Green
} else {
    Write-Host "✓ 远程仓库已配置: $remote" -ForegroundColor Green
}

# 设置主分支
Write-Host ""
Write-Host "[5/5] 设置主分支并推送..." -ForegroundColor Yellow
git branch -M main 2>$null

# 尝试推送
Write-Host "正在推送到 GitHub..." -ForegroundColor Yellow
try {
    git push -u origin main
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ 部署成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "你的项目已部署到 GitHub" -ForegroundColor Cyan
    Write-Host "仓库地址: $(git remote get-url origin)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "1. 在 GitHub 仓库页面添加 Topics (标签)" -ForegroundColor White
    Write-Host "2. 更新 README 中的 GitHub 链接" -ForegroundColor White
    Write-Host "3. 查看 GITHUB_DEPLOYMENT.md 了解更多" -ForegroundColor White
} catch {
    Write-Host ""
    Write-Host "推送失败，可能的原因:" -ForegroundColor Red
    Write-Host "1. 远程仓库不存在，请先在 GitHub 上创建仓库" -ForegroundColor Yellow
    Write-Host "2. 认证失败，请检查用户名和 token" -ForegroundColor Yellow
    Write-Host "3. 网络问题，请稍后重试" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "手动推送命令:" -ForegroundColor Cyan
    Write-Host "  git push -u origin main" -ForegroundColor White
}

Write-Host ""

