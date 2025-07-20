#!/bin/bash

# Twitter Bot 部署脚本

set -e

echo "🚀 开始部署 Twitter Bot..."

# 检查环境
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件"
    exit 1
fi

# 构建和启动
echo "🔨 构建镜像..."
docker-compose down
docker-compose build --no-cache

echo "📦 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查健康状态
echo "🔍 检查服务状态..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 部署成功！服务正在运行"
    echo "🔗 健康检查: http://localhost:8000/health"
    echo "📋 查看日志: docker-compose logs -f"
else
    echo "❌ 部署失败，服务未能正常启动"
    echo "📋 查看错误日志: docker-compose logs"
    exit 1
fi