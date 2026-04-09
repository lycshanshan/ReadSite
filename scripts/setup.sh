#!/usr/bin/env bash
# ReadSite 自动化配置脚本 - Linux / macOS 入口
# 用法: bash scripts/setup.sh
#       或先授权: chmod +x scripts/setup.sh && ./scripts/setup.sh

set -e

# 解析脚本自身所在目录（支持符号链接和不同 cwd 调用）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 查找 Python 3.12 ──────────────────────────────────────────────────────────
PYTHON_CMD=""
for cmd in python3.12 python3 python py; do
    if command -v "$cmd" > /dev/null 2>&1; then
        version=$("$cmd" --version 2>&1)
        if echo "$version" | grep -qE "Python 3\.12"; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "  ✗ 错误: 未找到 Python 3.12.x"
    echo ""
    echo "  请先安装 Python 3.12:"
    echo ""
    if [ "$(uname)" = "Darwin" ]; then
        echo "    macOS (Homebrew): brew install python@3.12"
        echo "    官网下载:         https://www.python.org/downloads/"
    elif [ -f /etc/debian_version ]; then
        echo "    Ubuntu/Debian:  sudo apt update && sudo apt install python3.12 python3.12-venv"
        echo "    官网下载:       https://www.python.org/downloads/"
    elif [ -f /etc/redhat-release ]; then
        echo "    CentOS/RHEL:  sudo dnf install python3.12"
        echo "    官网下载:     https://www.python.org/downloads/"
    else
        echo "    官网下载: https://www.python.org/downloads/"
    fi
    echo ""
    exit 1
fi

echo ""
echo "  ✓ 找到 Python: $($PYTHON_CMD --version)"
echo ""

# ── 调用主配置脚本，传入 Python 可执行文件路径 ────────────────────────────────
"$PYTHON_CMD" "$SCRIPT_DIR/setup.py" "$PYTHON_CMD" "$@"
