# GitHub 部署前检查脚本
# 用于检查哪些文件会被 Git 跟踪，哪些会被忽略

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub 部署前文件检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Git 是否已初始化
if (-not (Test-Path .git)) {
    Write-Host "⚠️  警告: 当前目录未初始化 Git 仓库" -ForegroundColor Yellow
    Write-Host "   请先运行: git init" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✅ Git 仓库已初始化" -ForegroundColor Green
    Write-Host ""
}

# 检查 .gitignore 是否存在
if (Test-Path .gitignore) {
    Write-Host "✅ .gitignore 文件存在" -ForegroundColor Green
} else {
    Write-Host "❌ .gitignore 文件不存在！" -ForegroundColor Red
    Write-Host "   请创建 .gitignore 文件" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "检查关键文件" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查必须存在的文件
$requiredFiles = @(
    "README.md",
    "LICENSE",
    "requirements.txt",
    "pyproject.toml",
    "src/quant_agent/__init__.py",
    "src/quant_agent/agent.py",
    "src/quant_agent/data.py",
    "src/quant_agent/strategy.py",
    "src/quant_agent/backtester.py"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file (缺失)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "检查应该被忽略的文件/目录" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查应该被忽略的文件/目录
$shouldIgnore = @(
    "quant_agent",
    "data_cache",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv"
)

foreach ($item in $shouldIgnore) {
    $found = Get-ChildItem -Path . -Filter $item -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        Write-Host "⚠️  发现: $item (应该被 .gitignore 忽略)" -ForegroundColor Yellow
    } else {
        Write-Host "✅ $item (未找到或已忽略)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git 状态检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path .git) {
    # 检查暂存区的文件
    $ErrorActionPreference = 'SilentlyContinue'
    $staged = git diff --cached --name-only
    if ($staged) {
        $stagedArray = @($staged)
        if ($stagedArray.Count -gt 0) {
            Write-Host "📦 已暂存的文件数量: $($stagedArray.Count)" -ForegroundColor Cyan
            Write-Host ""
        }
    }
    
    # 检查未跟踪的文件
    $untracked = git ls-files --others --exclude-standard
    if ($untracked) {
        $untrackedArray = @($untracked)
        if ($untrackedArray.Count -gt 0) {
            Write-Host "📝 未跟踪的文件数量: $($untrackedArray.Count)" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "前 20 个未跟踪的文件:" -ForegroundColor Yellow
            $untrackedArray | Select-Object -First 20 | ForEach-Object {
                Write-Host "  - $_" -ForegroundColor Gray
            }
            if ($untrackedArray.Count -gt 20) {
                Write-Host "  ... 还有 $($untrackedArray.Count - 20) 个文件" -ForegroundColor Gray
            }
        }
    }
    
    # 检查修改的文件
    $modified = git diff --name-only
    if ($modified) {
        $modifiedArray = @($modified)
        if ($modifiedArray.Count -gt 0) {
            Write-Host ""
            Write-Host "📝 已修改的文件数量: $($modifiedArray.Count)" -ForegroundColor Yellow
            Write-Host ""
        }
    }
    $ErrorActionPreference = 'Continue'
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "安全检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查可能包含敏感信息的文件
$sensitivePatterns = @(
    "*.key",
    "*.pem",
    ".env",
    "config.yaml",
    "secrets.yaml"
)

$foundSensitive = $false
foreach ($pattern in $sensitivePatterns) {
    $files = Get-ChildItem -Path . -Filter $pattern -Recurse -ErrorAction SilentlyContinue
    if ($files) {
        $foundSensitive = $true
        Write-Host "⚠️  警告: 发现可能包含敏感信息的文件:" -ForegroundColor Red
        $files | ForEach-Object {
            Write-Host "  - $($_.FullName)" -ForegroundColor Red
        }
    }
}

if (-not $foundSensitive) {
    Write-Host "✅ 未发现明显的敏感信息文件" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "文件大小检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查大文件（超过 10MB）
$largeFiles = Get-ChildItem -Path . -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 10MB } | 
    Sort-Object Length -Descending |
    Select-Object -First 10

if ($largeFiles) {
    Write-Host "⚠️  发现大文件（>10MB）:" -ForegroundColor Yellow
    $largeFiles | ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  - $($_.Name) ($sizeMB MB)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "提示: GitHub 建议单个文件不超过 100MB" -ForegroundColor Gray
} else {
    Write-Host "✅ 未发现大文件" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "建议的下一步操作" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path .git) {
    Write-Host "1. 查看详细的 Git 状态:" -ForegroundColor Cyan
    Write-Host "   git status" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. 添加所有文件到暂存区:" -ForegroundColor Cyan
    Write-Host "   git add ." -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. 提交更改:" -ForegroundColor Cyan
    Write-Host "   git commit -m 'Initial commit: Quant Trading Agent'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. 添加远程仓库:" -ForegroundColor Cyan
    Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/quant-trading-agent.git" -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. 推送到 GitHub:" -ForegroundColor Cyan
    Write-Host "   git push -u origin main" -ForegroundColor Gray
} else {
    Write-Host "1. 初始化 Git 仓库:" -ForegroundColor Cyan
    Write-Host "   git init" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. 然后按照上面的步骤继续" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "详细指南请查看: GITHUB_DEPLOYMENT_GUIDE_CN.md" -ForegroundColor Green
Write-Host ""

