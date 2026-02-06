#!/bin/bash
# Interactive Film Character Daily Agent 关闭脚本
# 关闭所有服务
# 支持任意克隆目录直接运行

echo "=========================================="
echo "  Interactive Film Character Daily Agent 服务关闭"
echo "=========================================="
echo ""

# 获取脚本所在目录作为工作目录（支持任意克隆目录）
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORK_DIR"

echo "工作目录: $WORK_DIR"
echo ""

# 1. 停止 Cloudflare Tunnel
echo "[1/2] 停止 Cloudflare Tunnel..."
pkill cloudflared
sleep 1

if pgrep -f "cloudflared" > /dev/null; then
    echo "       ⚠️  强制停止..."
    pkill -9 cloudflared
    sleep 1
fi

if ! pgrep -f "cloudflared" > /dev/null; then
    echo "       ✅ Cloudflare Tunnel 已停止"
else
    echo "       ❌ Cloudflare Tunnel 停止失败"
fi

# 2. 停止 Flask Web 服务
echo "[2/2] 停止 Flask Web 服务..."
pkill -f "web_interactive_demo.py"
sleep 1

# 如果进程还在，强制停止
if pgrep -f "web_interactive_demo.py" > /dev/null; then
    echo "       ⚠️  强制停止..."
    pkill -9 -f "web_interactive_demo.py"
    sleep 1
fi

if ! pgrep -f "web_interactive_demo.py" > /dev/null; then
    echo "       ✅ Flask 服务已停止"
else
    echo "       ❌ Flask 服务停止失败"
fi

echo ""
echo "=========================================="
echo "  所有服务已关闭"
echo "=========================================="
echo ""

# 显示状态
echo "当前状态："
echo ""
echo "端口占用："
ss -tlnp | grep -E ":(5000|20241)" || echo "  ✅ 端口 5000 和 20241 已释放"
echo ""
echo "进程状态："
ps aux | grep -E "cloudflared|web_interactive" | grep -v grep || echo "  ✅ 无相关进程运行"
