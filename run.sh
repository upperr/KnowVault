#!/bin/bash
# RAGFlow 一键重启脚本 - 重启后端 Docker 服务和前端开发服务器

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "🔄 一键重启 RAGFlow 服务"
echo "========================================"
echo ""

# 1. 重启后端 Docker 服务
echo "📦 重启后端 Docker 服务..."
docker compose -f docker/docker-compose-macos.yml restart

echo ""
echo "⏳ 等待后端服务就绪..."

# 使用正确的健康检查端点
MAX_RETRIES=12
RETRY_INTERVAL=5
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s http://localhost:9380/api/v1/system/healthz > /dev/null 2>&1; then
        echo "✅ 后端服务已就绪 (http://localhost:9380)"
        break
    else
        if [ $i -eq $MAX_RETRIES ]; then
            echo "⚠️  后端服务尚未就绪，请稍后检查"
            echo "💡 提示：使用 'docker logs docker-ragflow-1 -f' 查看后端日志"
        else
            echo "   等待中... ($i/$MAX_RETRIES)"
            sleep $RETRY_INTERVAL
        fi
    fi
done

# 2. 重启前端开发服务器
echo ""
echo "🌐 重启前端开发服务器..."

# 查找并终止现有的前端进程
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    echo "📋 检测到前端进程 (PID: $FRONTEND_PID)，正在终止..."
    kill $FRONTEND_PID 2>/dev/null || true
    sleep 2
fi

# 在后台启动前端开发服务器
cd web
echo "▶️  启动前端开发服务器..."
nohup npm run dev > ../.frontend-dev.log 2>&1 &
FRONTEND_NEW_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_NEW_PID)"

# 等待前端启动
sleep 3
echo ""
echo "========================================"
echo "📝 服务信息:"
echo "   后端 API:  http://localhost:9380"
echo "   前端地址：http://localhost:3000"
echo "   前端日志：../.frontend-dev.log"
echo "========================================"
echo ""
echo "💡 提示：使用 'tail -f .frontend-dev.log' 查看前端日志"
