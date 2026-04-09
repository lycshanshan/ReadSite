#!/usr/bin/env bash
# ReadSite 服务器端自动化更新脚本 - Linux
# 功能: 关闭 Gunicorn 服务 -> 执行数据迁移 -> 收集静态文件 -> 重启服务
# 用法: bash scripts/update.sh
#       或先授权: chmod +x scripts/update.sh && ./scripts/update.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# ── 检查虚拟环境 ──────────────────────────────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
    echo ""
    echo "  ✗ 未找到虚拟环境: $PROJECT_ROOT/venv/"
    echo ""
    echo "  请确保已在服务器环境运行过 setup.sh 完成初始化部署。"
    echo ""
    exit 1
fi

cd "$PROJECT_ROOT"

# ── 停止服务 ──────────────────────────────────────────────────────────────────
echo ""
echo "  ▶ 正在停止 Gunicorn 服务 (可能需要输入 sudo 密码)..."
sudo systemctl stop readsite
echo "  ✓ 服务已停止"

# ── Django 维护操作 ───────────────────────────────────────────────────────────
echo ""
echo "  ▶ 执行 makemigrations..."
"$VENV_PYTHON" manage.py makemigrations

echo ""
echo "  ▶ 执行 migrate..."
"$VENV_PYTHON" manage.py migrate

echo ""
echo "  ▶ 收集静态文件 (collectstatic)..."
"$VENV_PYTHON" manage.py collectstatic --noinput

# ── 重启服务 ──────────────────────────────────────────────────────────────────
echo ""
echo "  ▶ 正在重新启动 Gunicorn 服务..."
sudo systemctl start readsite

# 检查服务状态
echo ""
echo "  ▶ 当前服务状态:"
sudo systemctl status readsite --no-pager | grep -E "Active:|Main PID:"

echo ""
echo "  ✓ 更新部署完成！网站已恢复运行。"
echo ""