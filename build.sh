#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== [1/5] 正在检查构建环境 ==="

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
echo "=== [2/5] 正在校验依赖 ==="
if [ ! -f "$PROJECT_DIR/requirements-freeze.txt" ]; then
    echo "【错误】找不到 requirements-freeze.txt" >&2
    exit 1
fi

"$PYTHON" -m pip install --upgrade pip --quiet
"$PYTHON" -m pip install -r "$PROJECT_DIR/requirements-freeze.txt" --quiet
#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== [1/5] 正在检查构建环境 ==="

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
echo "=== [2/5] 正在校验依赖 ==="
if [ ! -f "$PROJECT_DIR/requirements-freeze.txt" ]; then
    echo "【错误】找不到 requirements-freeze.txt" >&2
    exit 1
fi

"$PYTHON" -m pip install --upgrade pip --quiet
"$PYTHON" -m pip install -r "$PROJECT_DIR/requirements-freeze.txt" --quiet
"$PYTHON" -m pip install pyinstaller --quiet

# 4. 打包
echo "=== [3/5] 正在执行 PyInstaller 打包 ==="
WORK_DIR="$(mktemp -d -t instant-tanuki-build.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

# 把输出重定向去掉了，让 CI 能看到红字
"$PYTHON" -m PyInstaller --noconfirm \
  --distpath "$WORK_DIR/dist" \
  --workpath "$WORK_DIR/build" \
  InstantTanukiMaker.spec

echo "=== [4/5] 正在组装外置资源 ==="
out="$WORK_DIR/dist/InstantTanukiMaker"

# 把 -d 改成 -e 兼容文件和文件夹 (加入 LICENSE)
for res in "Material" "添加" "locale" "LICENSE" "LICENSE_zh"; do
    if [ -e "$PROJECT_DIR/$res" ]; then
        cp -r "$PROJECT_DIR/$res" "$out/$res"
    else
        echo "【警告】未找到资源: $res"
    fi
done

echo "=== [5/5] 正在压缩产物 ==="
DOWNLOAD_DIR="${XDG_DOWNLOAD_DIR:-$HOME/Downloads}"
if [ ! -d "$DOWNLOAD_DIR" ]; then
    if [ -d "$HOME/下载" ]; then DOWNLOAD_DIR="$HOME/下载"; else mkdir -p "$DOWNLOAD_DIR"; fi
fi
OUT_FILE="$DOWNLOAD_DIR/InstantTanukiMaker-linux-x64.tar.zst"

# 确认有 zstd 才压缩
if command -v zstd >/dev/null 2>&1; then
    tar -C "$out" -cf - . | zstd -19 -T0 -o "$OUT_FILE"
else
    echo "【错误】未找到 zstd 命令！" >&2
    exit 1
fi

echo "已成功构建：$OUT_FILE"
ls -lh "$OUT_FILE"
