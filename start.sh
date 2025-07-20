#!/bin/bash

# Twitter Bot 启动脚本

echo "🚀 启动 Twitter Bot..."

echo "📥 正在从 Git 拉取最新代码..."
git pull origin main

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，请先创建:"
    echo "python3 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件，请创建并配置:"
    echo "cp .env.example .env"
    echo "然后编辑 .env 文件，填入你的API密钥"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
python -c "import telegram, tweepy, aiohttp, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 依赖包缺失，正在安装..."
    pip install -r requirements.txt
fi

echo "✅ 环境准备完毕！"