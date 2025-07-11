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

## 部署到Railway

### 1. 准备部署
1. 将代码推送到GitHub仓库
2. 访问 [Railway](https://railway.app/)
3. 注册并连接GitHub账户

### 2. 创建项目
1. 点击"New Project"
2. 选择"Deploy from GitHub repo"
3. 选择你的仓库

### 3. 配置环境变量
在Railway项目设置中添加以下环境变量：
- `TELEGRAM_BOT_TOKEN`
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`
- `TWITTER_BEARER_TOKEN`

### 4. 部署
Railway会自动检测Dockerfile并进行部署。

## 使用方法
1. 在Telegram中找到你的机器人
2. 发送 `/start` 开始使用
3. 直接发送文本消息，机器人会自动转发到Twitter
4. 使用 `/help` 查看帮助信息

## 注意事项
- 消息长度不能超过280字符
- 确保Twitter API有发推权限
- 保护好你的API密钥