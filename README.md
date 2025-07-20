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

### 5. 配置Twitter私信接收（可选）
如果需要接收Twitter私信：
1. 在Twitter Developer Portal中配置webhook URL：
   - Webhook URL: `https://your-domain.com/webhook/twitter`
   - 设置webhook secret并添加到环境变量
2. 确保你的应用有私信权限
3. 测试webhook连接

### 6. 运行机器人

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

## 使用方法
1. 在Telegram中找到你的机器人
2. 发送 `/start` 开始使用
3. 直接发送文本消息，机器人会自动转发到Twitter
4. 发送图片（可带文字描述），机器人会上传图片到Twitter
5. 使用 `/help` 查看帮助信息

## 功能特性
- ✅ 文本推文发送
- ✅ 图片推文发送（自动优化压缩）
- ✅ Twitter私信接收和转发到Telegram（隔离式设计）
- ✅ 用户权限验证
- ✅ 自动保活机制
- ✅ DM功能故障不影响主要功能
- ✅ 按需启用私信监听（/dm 命令）

## 注意事项
- 消息长度不能超过280字符
- 图片会自动压缩优化以符合Twitter要求
- 确保Twitter API有发推和私信权限
- 私信功能需要配置webhook和公网访问
- 私信API失败不会影响推文发送功能
- 使用 `/dm` 命令可按需启用私信监听
- 保护好你的API密钥