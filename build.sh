#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "正在检查构建环境..."

# 1. 找 Python
SYS_PYTHON=""
if command -v python3 >/dev/null 2>&1; then SYS_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then SYS_PYTHON="python"
fi

if [ -z "$SYS_PYTHON" ]; then
    echo "【错误】未找到 Python 3。" >&2
    echo "建议执行：sudo apt install python3 python3-venv" >&2
    exit 1
fi

# 2. 检查/创建 venv
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "正在创建虚拟环境..."
    "$SYS_PYTHON" -m venv "$VENV_DIR"
    echo "虚拟环境创建完毕。"
fi

# 3. 处理依赖
echo "正在读取 requirements-freeze.txt..."
if [ ! -f "$PROJECT_DIR/requirements-freeze.txt" ]; then
    echo "【错误】找不到 requirements-freeze.txt" >&2
    exit 1
fi

echo "正在检查已安装的依赖..."
if ! "$PYTHON" -m pip check >/dev/null 2>&1; then
    echo "正在解析依赖关系..."
    "$PYTHON" -m pip install --upgrade pip --quiet
    "$PYTHON" -m pip install -r "$PROJECT_DIR/requirements-freeze.txt"
else
    # 如果依赖完整，但缺 pyinstaller，单独装
    if ! "$PYTHON" -c "import PyInstaller" >/dev/null 2>&1; then
        echo "正在安装 PyInstaller..."
        "$PYTHON" -m pip install pyinstaller
    fi
fi

# 4. 打包 (完全 APT 风格)
echo "正在准备打包..."
WORK_DIR="$(mktemp -d -t instant-tanuki-build.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "正在执行 PyInstaller..."
"$PYTHON" -m PyInstaller --noconfirm \
  --distpath "$WORK_DIR/dist" \
  --workpath "$WORK_DIR/build"

echo "正在组装外置资源..."
out="$WORK_DIR/dist/InstantTanukiMaker"
cp -r Material "$out/Material"
cp -r 添加     "$out/添加"
cp -r locale   "$out/locale"

echo "正在压缩产物..."
DOWNLOAD_DIR="${XDG_DOWNLOAD_DIR:-$HOME/Downloads}"
if [ ! -d "$DOWNLOAD_DIR" ]; then
    if [ -d "$HOME/下载" ]; then DOWNLOAD_DIR="$HOME/下载"; else mkdir -p "$DOWNLOAD_DIR"; fi
fi
OUT_FILE="$DOWNLOAD_DIR/InstantTanukiMaker-linux-x64.tar.zst"
tar -C "$out" -cf - . | zstd -19 -T0 -o "$OUT_FILE"

echo "已成功构建：$OUT_FILE"
ls -lh "$OUT_FILE"
