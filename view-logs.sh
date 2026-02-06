#!/bin/bash
# 查看访问日志

echo "=========================================="
echo "  Interactive Film Character Daily Agent 访问日志"
echo "=========================================="
echo ""
echo "选择查看内容："
echo "  1) Flask 实时访问日志"
echo "  2) Cloudflare Tunnel 实时日志"
echo "  3) Flask 最近 50 条访问记录"
echo "  4) 当前在线访问统计"
echo "  5) 退出"
echo ""
read -p "请选择 [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "=== Flask 实时访问日志 (Ctrl+C 退出) ==="
        echo ""
        # 使用 cat 保留 ANSI 颜色代码
        tail -f /tmp/zooo-agent.log | cat
        ;;
    2)
        echo ""
        echo "=== Cloudflare Tunnel 实时日志 (Ctrl+C 退出) ==="
        echo ""
        # Cloudflare 日志本身带颜色，直接显示
        tail -f /tmp/cloudflared.log
        ;;
    3)
        echo ""
        echo "=== Flask 最近 50 条访问记录 ==="
        echo ""
        # 直接读取日志文件，保留颜色
        tail -100 /tmp/zooo-agent.log | cat
        ;;
    4)
        echo ""
        echo "=== 当前连接统计 ==="
        echo ""
        echo "Flask 服务状态："
        systemctl status zooo-agent --no-pager | head -10
        echo ""
        echo "当前端口连接："
        ss -tnp | grep :5000 | wc -l | xargs echo "  连接数:"
        ss -tnp | grep :5000
        echo ""
        echo "Cloudflare Tunnel 状态："
        pgrep -f cloudflared > /dev/null && echo "  ✅ 运行中" || echo "  ❌ 未运行"
        ;;
    5)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac
