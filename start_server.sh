#!/bin/bash

# Hush 后端服务器启动脚本
# 使用方法：./start_server.sh

cd "$(dirname "$0")" || exit

echo "🚀 Hush 后端服务启动中..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  应用访问地址："
echo "  👉 http://localhost:8000/hush_app.html"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 加载 .env 文件
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "✓ 已加载 .env 配置"
else
    echo "⚠️  找不到 .env 文件"
fi

# 启动服务
python3 hush_backend.py
