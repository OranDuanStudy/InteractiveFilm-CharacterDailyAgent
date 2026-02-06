#!/bin/bash
# Interactive Film Character Daily Agent 完整启动脚本
# 从完全关闭状态启动所有服务

#   ---                                                                                                                                                                                          
#   使用方法                                                                                                                                                                                     
                                                                                                                                                                                               
#   # 关闭所有                                                                                                                                                                                   
#   ./stop-all.sh                                                                                                                                                                                
                                                                                                                                                                                               
#   # 启动所有                                                                                                                                                                                   
#   ./start-tunnel.sh                                                                                                                                                                            
                                                                                                                                                                                               
#   # 查看隧道地址                                                                                                                                                                               
#   tail -50 /tmp/cloudflared.log | grep 'https://'                                                                                                                                              
                                                                                                                                                                                               
#   ---                                                           

echo "=========================================="
echo "  Interactive Film Character Daily Agent 服务启动"
echo "=========================================="
echo ""

# 工作目录 - 获取脚本所在目录（支持任意克隆目录）
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORK_DIR"

echo "工作目录: $WORK_DIR"
echo ""

# 1. 启动 Flask Web 服务（直接运行，无需systemd服务）
echo "[1/2] 启动 Flask Web 服务..."

# 检查是否已有Flask进程在运行
if pgrep -f "web_interactive_demo.py" > /dev/null; then
    echo "       ⚠️  Flask 服务已在运行，跳过启动"
else
    # 直接启动Flask（保留颜色输出）
    # FORCE_COLOR=1 确保即使检测到不是终端也会输出颜色
    # PYTHONUNBUFFERED=1 确保 Python 输出不被缓冲
    FORCE_COLOR=1 PYTHONUNBUFFERED=1 nohup python web_interactive_demo.py > /tmp/zooo-agent.log 2>&1 &
fi

# 等待服务启动
sleep 3

# 检查 Flask 服务状态
if pgrep -f "web_interactive_demo.py" > /dev/null; then
    echo "       ✅ Flask 服务已启动 (端口 5000)"
    echo "       日志: tail -f /tmp/zooo-agent.log"
else
    echo "       ❌ Flask 服务启动失败"
    echo "       查看: tail /tmp/zooo-agent.log"
    exit 1
fi

# 2. 启动 Cloudflare Tunnel
echo "[2/2] 启动 Cloudflare Tunnel..."
nohup cloudflared tunnel --url http://localhost:5000 --loglevel info > /tmp/cloudflared.log 2>&1 &

# 等待隧道启动
sleep 5

# 检查隧道状态
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "       ✅ Cloudflare Tunnel 已启动"
    echo ""
    echo "=========================================="
    echo "  所有服务启动成功！"
    echo "=========================================="
    echo ""
    echo "访问地址："
    echo "  本地:  http://localhost:5000"
    echo "  公网:  https://xxxxxxxx.trycloudflare.com"
    echo ""
    echo "Cloudflare Tunnel 日志："
    tail -50 /tmp/cloudflared.log | grep 'https://'
else
    echo "       ❌ Cloudflare Tunnel 启动失败"
    echo "       查看: tail /tmp/cloudflared.log"
    exit 1
fi
