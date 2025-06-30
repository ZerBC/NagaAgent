# 一键配置脚本 for NagaAgent 3.0 (极致码高尔夫)
# 版本号由config.py统一管理
$ErrorActionPreference = "Stop" # 设置错误时停止执行
$pythonMinVersion = "3.8" # Python最低版本要求
$venvPath = ".venv" # 虚拟环境路径

# 检查Python版本
$pythonVersion = (python --version 2>&1) -replace "Python "
if ([version]$pythonVersion -lt [version]$pythonMinVersion) {
    Write-Error "需要Python $pythonMinVersion或更高版本，当前版本: $pythonVersion"
    exit 1
}

# 设置工作目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# 创建并激活虚拟环境
if (-not (Test-Path $venvPath)) {
    Write-Host "创建虚拟环境..."
    python -m venv $venvPath
}

# 激活虚拟环境
. "$venvPath/Scripts/Activate.ps1"

# 安装依赖（用清华源加速）
Write-Host "安装依赖（使用清华镜像源加速）..."
Get-ChildItem -Filter "requirements*.txt" | ForEach-Object {
    pip install -r $_.FullName -i https://pypi.tuna.tsinghua.edu.cn/simple
}

# 安装playwright浏览器驱动
Write-Host "安装playwright浏览器驱动..."
python -m playwright install chromium

# 验证playwright安装
Write-Host "验证playwright安装..."
$playwrightVersion = python -m playwright --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Playwright安装验证失败"
    exit 1
}
Write-Host "Playwright版本: $playwrightVersion"

Write-Host "环境设置完成！"
Write-Host "如需安装其他浏览器驱动，请运行:"
Write-Host "python -m playwright install firefox  # 安装Firefox"
Write-Host "python -m playwright install webkit   # 安装WebKit" 