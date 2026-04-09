#!/usr/bin/env bash
# ReadSite 快速开发启动脚本 - Linux / macOS
# 功能: 激活虚拟环境，执行数据库迁移，启动 runserver
# 用法: bash scripts/dev.sh
#       或先授权: chmod +x scripts/dev.sh && ./scripts/dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# ── 检查虚拟环境 ──────────────────────────────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
    echo ""
    echo "  ✗ 未找到虚拟环境: $PROJECT_ROOT/venv/"
    echo ""
    echo "  请先运行配置脚本完成初始化:"
    echo "    bash scripts/setup.sh"
    echo ""
    exit 1
fi

cd "$PROJECT_ROOT"

echo ""
echo "  ▶ 执行数据库迁移..."
"$VENV_PYTHON" manage.py makemigrations
"$VENV_PYTHON" manage.py migrate

echo ""
echo "  ▶ 启动开发服务器..."
echo "    访问地址: http://127.0.0.1:8000"
echo "    API 文档: http://127.0.0.1:8000/api/docs/"
echo "    按 Ctrl+C 停止"
echo ""
"$VENV_PYTHON" manage.py runserver
