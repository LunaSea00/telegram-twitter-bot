# Telegram to Twitter Bot

自动将Telegram消息发送到Twitter的机器人。

## 设置步骤

### 1. 创建Telegram Bot
1. 在Telegram中搜索 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 保存获得的Bot Token

### 2. 申请Twitter API
1. 访问 [Twitter Developer Portal](https://developer.twitter.com/)
2. **创建项目**：
   - 点击"Projects & Apps" → "Overview"
   - 点击"Create Project"
   - 填写项目信息
3. **创建/关联应用**：
   - 在项目中点击"Add App"
   - 创建新应用或关联现有应用
4. **配置App权限**：
   - 在App设置中：
   - App permissions设置为"Read and write"
   - Type of App选择"Web App"
5. 获取以下密钥：
   - API Key
   - API Secret
   - Access Token (权限修改后重新生成)
   - Access Token Secret (权限修改后重新生成)
   - **Bearer Token** (在项目的Keys and tokens页面生成)

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
1. 复制 `.env.example` 为 `.env`
2. 填入你的API密钥

### 5. 运行机器人

#### 本地运行
```bash
python bot.py
```

#### Docker运行
```bash
# 构建镜像
docker build -t telegram-twitter-bot .

# 运行容器
docker run -d --name telegram-bot --env-file .env telegram-twitter-bot
```

## 部署到Fly.io

### 1. 安装Fly CLI
```bash
# macOS/Linux
curl -L https://fly.io/install.sh | sh

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### 2. 登录并初始化
```bash
# 登录Fly.io
fly auth login

# 在项目目录中初始化（可选，已有fly.toml）
fly launch --no-deploy
```

### 3. 配置环境变量
```bash
fly secrets set TELEGRAM_BOT_TOKEN=你的telegram_bot_token
fly secrets set TWITTER_API_KEY=你的twitter_api_key
fly secrets set TWITTER_API_SECRET=你的twitter_api_secret
fly secrets set TWITTER_ACCESS_TOKEN=你的twitter_access_token
fly secrets set TWITTER_ACCESS_TOKEN_SECRET=你的twitter_access_token_secret
fly secrets set TWITTER_BEARER_TOKEN=你的twitter_bearer_token
```

### 4. 部署
```bash
fly deploy
```

### 5. 查看状态
```bash
fly status
fly logs
```

## 使用方法
1. 在Telegram中找到你的机器人
2. 发送 `/start` 开始使用
3. 直接发送文本消息，机器人会自动转发到Twitter
4. 使用 `/help` 查看帮助信息

## 注意事项
- 消息长度不能超过280字符
- 确保Twitter API有发推权限
- 保护好你的API密钥