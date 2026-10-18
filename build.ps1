$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

Write-Host "正在检查构建环境..."

# 1. 找 Python
$SysPython = $null
if (Get-Command "py" -ErrorAction SilentlyContinue) { $SysPython = "py" }
elseif (Get-Command "python" -ErrorAction SilentlyContinue) { $SysPython = "python" }

if (-not $SysPython) {
    Write-Host "【错误】未找到 Python 3。" -ForegroundColor Red
    Write-Host "建议前往 https://www.python.org/downloads/ 下载并安装。" -ForegroundColor Red
    exit 1
}

# 2. 检查/创建 venv
$VenvDir = Join-Path $ProjectDir "venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "正在创建虚拟环境..."
    & $SysPython -m venv $VenvDir
    Write-Host "虚拟环境创建完毕。"
}

# 3. 处理依赖
Write-Host "正在读取 requirements-freeze.txt..."
$ReqFile = Join-Path $ProjectDir "requirements-freeze.txt"
if (-not (Test-Path $ReqFile)) {
    Write-Host "【错误】找不到 requirements-freeze.txt" -ForegroundColor Red
    exit 1
}

Write-Host "正在解析依赖关系..."
& $PythonExe -c "import PyInstaller, PySide6" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安装依赖..."
    & $PythonExe -m pip install --upgrade pip --quiet
    & $PythonExe -m pip install -r $ReqFile
    & $PythonExe -m pip install pyinstaller
} else {
    # 依赖完整，缺 PyInstaller 就补
    & $PythonExe -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "正在安装 PyInstaller..."
        & $PythonExe -m pip install pyinstaller
    }
}

# 4. 打包
Write-Host "正在准备打包..."
$WorkDir = Join-Path $env:TEMP ("instant-tanuki-build-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

try {
    Write-Host "正在执行 PyInstaller..."
    & $PythonExe -m PyInstaller --noconfirm `
        --distpath "$WorkDir\dist" `
        --workpath "$WorkDir\build" `
        InstantTanukiMaker.spec *> $null

    Write-Host "正在组装外置资源..."
    $out = "$WorkDir\dist\InstantTanukiMaker"
    Copy-Item -Recurse -Force Material "$out\Material"
    Copy-Item -Recurse -Force 添加     "$out\添加"
    Copy-Item -Recurse -Force locale   "$out\locale"

    Write-Host "正在压缩产物..."
    $DownloadDir = Join-Path $env:USERPROFILE "Downloads"
    if (-not (Test-Path $DownloadDir)) { New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null }
    $OutFile = Join-Path $DownloadDir "InstantTanukiMaker-win-x64.zip"
    Compress-Archive -Path "$out\*" -DestinationPath $OutFile -Force

    Write-Host "已成功构建：$OutFile" -ForegroundColor Green
    Get-Item $OutFile | Format-List Name, Length
}
finally {
    Remove-Item -Recurse -Force $WorkDir -ErrorAction SilentlyContinue
}
