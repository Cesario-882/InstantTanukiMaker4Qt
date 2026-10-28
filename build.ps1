$ErrorActionPreference = 'Stop'
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

# 判断是否在 CI 环境中 (GitHub Actions 会自动注入 CI=true)
$IsCI = $env:CI -eq "true"

Write-Host "=== [1/5] 正在检查构建环境 ===" -ForegroundColor Cyan

# 1. 找 Python (优先 py 启动器)
$SysPython = $null
if (Get-Command "py" -ErrorAction SilentlyContinue) { $SysPython = "py" }
elseif (Get-Command "python" -ErrorAction SilentlyContinue) { $SysPython = "python" }

if (-not $SysPython) {
    Write-Host "【错误】未找到 Python 3。请前往 https://www.python.org/downloads/ 下载并安装，并勾选 'Add to PATH'。" -ForegroundColor Red
    exit 1
}

# 2. 检查/创建 venv
$VenvDir = Join-Path $ProjectDir "venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "正在创建虚拟环境..."
    & $SysPython -m venv $VenvDir
}

# 3. 处理依赖及环境验证
Write-Host "=== [2/5] 正在校验依赖与环境 (可能需要 MSVC) ===" -ForegroundColor Cyan
$ReqFile = Join-Path $ProjectDir "requirements-freeze.txt"
if (-not (Test-Path $ReqFile)) {
    Write-Host "【错误】找不到 requirements-freeze.txt" -ForegroundColor Red
    exit 1
}

# 升级 pip 并静默安装依赖
Write-Host "正在检查/安装依赖包..."
& $PythonExe -m pip install --upgrade pip --quiet
& $PythonExe -m pip install -r $ReqFile --quiet
& $PythonExe -m pip install pyinstaller --quiet

# 验证环境并捕获 MSVC 相关的编译错误
Write-Host "正在验证 PySide6 与 PyInstaller 的完整性..."
$checkCmd = "import PyInstaller, PySide6; print('Dependencies OK')"
$checkResult = & $PythonExe -c $checkCmd 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "【严重错误】依赖导入失败！" -ForegroundColor Red
    Write-Host "这可能是因为缺少 MSVC C++ 编译环境（PySide6 底层扩展编译失败）。" -ForegroundColor Yellow
    Write-Host "请前往 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 下载" -ForegroundColor Yellow
    Write-Host "安装时务必勾选 '使用 C++ 的桌面开发' (Desktop development with C++)。" -ForegroundColor Yellow
    Write-Host "原始错误信息:`n$checkResult" -ForegroundColor Gray
    exit 1
} else {
    Write-Host "环境验证通过！" -ForegroundColor Green
}

# 4. 打包
Write-Host "=== [3/5] 正在执行 PyInstaller 打包 ===" -ForegroundColor Cyan
$WorkDir = Join-Path $env:TEMP ("instant-tanuki-build-" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

try {
    & $PythonExe -m PyInstaller --noconfirm `
        --distpath "$WorkDir\dist" `
        --workpath "$WorkDir\build" `
        InstantTanukiMaker.spec

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 构建失败，请检查 spec 文件或源码。"
    }

    Write-Host "=== [4/5] 正在组装外置资源 ===" -ForegroundColor Cyan
    $out = "$WorkDir\dist\InstantTanukiMaker"

    # 检查外置资源目录是否存在再复制 (加入 LICENSE)
    $resources = @("Material", "添加", "locale", "LICENSE", "LICENSE_zh")
    foreach ($res in $resources) {
        $srcPath = Join-Path $ProjectDir $res
        if (Test-Path $srcPath) {
            Copy-Item -Recurse -Force $srcPath "$out\$res"
        } else {
            Write-Host "【警告】未找到资源: $res" -ForegroundColor Yellow
        }
    }

    Write-Host "=== [5/5] 正在高速压缩产物 ===" -ForegroundColor Cyan
    $DownloadDir = Join-Path $env:USERPROFILE "Downloads"
    if (-not (Test-Path $DownloadDir)) { New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null }

    $OutFile = Join-Path $DownloadDir "InstantTanukiMaker-win-x64.zip"

    if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($out, $OutFile, [System.IO.Compression.CompressionLevel]::Optimal, $false)

    Write-Host "构建成功：$OutFile" -ForegroundColor Green
    $FileSize = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
    Write-Host "文件大小：$FileSize MB" -ForegroundColor Green

} catch {
    Write-Host "【构建失败】$_" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item -Recurse -Force $WorkDir -ErrorAction SilentlyContinue
}

if (-not $IsCI) {
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
