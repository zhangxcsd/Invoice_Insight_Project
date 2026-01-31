# ============================================================================
# 一键打包脚本 - 增值税发票审计系统 GUI 版本
# ============================================================================
# 功能：
#   1. 检查环境和依赖
#   2. 清理旧的打包文件
#   3. 使用 PyInstaller 打包
#   4. 验证打包结果
#   5. 创建发布包
# 
# 使用方法：
#   .\build_exe.ps1
#   或
#   .\build_exe.ps1 -Clean    # 清理并重新打包
#   .\build_exe.ps1 -Debug    # 调试模式（生成目录而非单文件）
# ============================================================================

param(
    [switch]$Clean,    # 清理旧文件
    [switch]$Debug     # 调试模式
)

# 设置错误时停止
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Step {
    param([string]$Message)
    Write-ColorOutput "`n==> $Message" -Color Cyan
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✓ $Message" -Color Green
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "✗ $Message" -Color Red
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠ $Message" -Color Yellow
}

# ============================================================================
# 步骤 1: 环境检查
# ============================================================================
Write-Step "检查 Python 环境..."

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python 已安装: $pythonVersion"
}
catch {
    Write-Error "未找到 Python！请先安装 Python 3.8 或更高版本。"
    exit 1
}

# 检查 pip 是否可用
try {
    $pipVersion = pip --version 2>&1
    Write-Success "pip 已安装: $pipVersion"
}
catch {
    Write-Error "未找到 pip！请检查 Python 安装。"
    exit 1
}

# ============================================================================
# 步骤 2: 安装/更新依赖
# ============================================================================
Write-Step "检查并安装依赖..."

# 检查 PyInstaller 是否安装
$pyinstallerInstalled = pip list 2>&1 | Select-String "pyinstaller"
if (-not $pyinstallerInstalled) {
    Write-Warning "PyInstaller 未安装，正在安装..."
    pip install pyinstaller
    Write-Success "PyInstaller 安装完成"
}
else {
    Write-Success "PyInstaller 已安装"
}

# 安装项目依赖
if (Test-Path "requirements.txt") {
    Write-ColorOutput "安装项目依赖..." -Color Yellow
    pip install -r requirements.txt --quiet
    Write-Success "依赖安装完成"
}

# ============================================================================
# 步骤 3: 清理旧文件（可选）
# ============================================================================
if ($Clean) {
    Write-Step "清理旧的打包文件..."
    
    $cleanDirs = @("build", "dist")
    foreach ($dir in $cleanDirs) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
            Write-Success "已删除 $dir 目录"
        }
    }
    
    if (Test-Path "*.spec") {
        # 保留我们的 vat_gui.spec，删除其他自动生成的
        Get-ChildItem -Filter "*.spec" | Where-Object { $_.Name -ne "vat_gui.spec" } | Remove-Item -Force
    }
}

# ============================================================================
# 步骤 4: 执行打包
# ============================================================================
Write-Step "开始打包程序..."

# 确定使用的 spec 文件
$specFile = "vat_gui.spec"

if (-not (Test-Path $specFile)) {
    Write-Error "未找到 $specFile 配置文件！"
    exit 1
}

# 如果是调试模式，需要修改 spec 文件（使用目录模式）
if ($Debug) {
    Write-Warning "调试模式：将生成目录结构而非单文件"
    # 这里可以临时修改 spec 文件或使用不同的配置
}

# 执行 PyInstaller
Write-ColorOutput "正在打包，请稍候..." -Color Yellow
try {
    pyinstaller $specFile --clean --noconfirm
    Write-Success "打包完成！"
}
catch {
    Write-Error "打包失败: $_"
    exit 1
}

# ============================================================================
# 步骤 5: 验证打包结果
# ============================================================================
Write-Step "验证打包结果..."

$exePath = "dist\VAT_Invoice_Processor.exe"
if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Success "可执行文件已生成: $exePath"
    Write-ColorOutput "文件大小: $([math]::Round($exeSize, 2)) MB" -Color Cyan
}
else {
    Write-Error "未找到打包后的可执行文件！"
    exit 1
}

# ============================================================================
# 步骤 6: 创建发布包
# ============================================================================
Write-Step "创建发布包..."

$releaseDir = "Release"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$releaseSubDir = "$releaseDir\VAT_Audit_System_$timestamp"

# 创建发布目录
if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

New-Item -ItemType Directory -Path $releaseSubDir | Out-Null

# 复制可执行文件
Copy-Item $exePath -Destination $releaseSubDir
Write-Success "已复制可执行文件"

# 复制配置文件模板
if (Test-Path "config_default.yaml") {
    Copy-Item "config_default.yaml" -Destination "$releaseSubDir\config_default.yaml"
    Write-Success "已复制配置文件模板"
}

# 创建必要的目录结构
$requiredDirs = @("Source_Data", "Outputs", "Database")
foreach ($dir in $requiredDirs) {
    New-Item -ItemType Directory -Path "$releaseSubDir\$dir" -Force | Out-Null
}
Write-Success "已创建目录结构"

# 复制使用说明（如果存在）
if (Test-Path "BUILD_AND_PACKAGE.md") {
    Copy-Item "BUILD_AND_PACKAGE.md" -Destination "$releaseSubDir\使用说明.md"
    Write-Success "已复制使用说明"
}

# 创建快速启动说明
$quickStart = @"
# 增值税发票审计系统 - 使用说明

## 快速开始

1. 双击运行 VAT_Invoice_Processor.exe
2. 在界面中配置输入/输出目录
3. 点击"开始处理"按钮
4. 查看实时日志和进度
5. 处理完成后，在输出目录中查看结果

## 目录说明

- Source_Data/   : 放置原始 Excel 数据文件
- Outputs/       : 处理结果和报告输出位置
- Database/      : 数据库文件存储位置
- config_default.yaml : 配置文件模板（可选）

## 数据要求

输入的 Excel 文件应包含发票数据，支持 .xlsx 和 .xls 格式。

## 技术支持

如遇问题，请查看程序界面中的日志信息。

版本: 1.0.1
日期: $(Get-Date -Format 'yyyy-MM-dd')
"@

$quickStart | Out-File -FilePath "$releaseSubDir\README.txt" -Encoding UTF8
Write-Success "已创建快速启动说明"

# ============================================================================
# 完成
# ============================================================================
Write-Step "打包完成！"
Write-ColorOutput "`n发布包位置: $releaseSubDir" -Color Green
Write-ColorOutput "`n可以直接将该文件夹分发给用户使用。" -Color Yellow

# 询问是否打开发布目录
$openDir = Read-Host "`n是否打开发布目录？(Y/N)"
if ($openDir -eq 'Y' -or $openDir -eq 'y') {
    explorer $releaseSubDir
}

Write-ColorOutput "`n✓ 全部完成！" -Color Green
