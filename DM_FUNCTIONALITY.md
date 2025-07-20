# 🔍 Twitter私信监听功能

## 概述
该功能为TwitterBot新增了监听Twitter私信并转发到Telegram的能力，实现了完整的双向通信桥梁。

## 🚀 核心功能

### 1. 自动私信监听
- **轮询机制**: 定期检查Twitter私信（默认60秒间隔）
- **实时转发**: 新私信自动转发到指定Telegram聊天
- **去重处理**: 避免重复推送相同私信
- **媒体支持**: 支持转发私信中的图片、视频等媒体

### 2. 智能消息处理
- **发送者识别**: 显示私信发送者的用户名和昵称
- **时间戳**: 准确显示私信发送时间
- **格式化显示**: 优雅的Markdown格式通知
- **媒体处理**: 自动下载并转发媒体文件

### 3. 可靠性保障
- **错误恢复**: 网络异常后自动重试
- **频率限制**: 遵守Twitter API调用限制
- **数据持久化**: 本地存储已处理私信记录
- **优雅停止**: 支持服务的安全启停

## 📂 模块架构

```
src/dm/
├── monitor.py      # 私信监听器 - 核心轮询逻辑
├── processor.py    # 消息处理器 - 解析和格式化
├── notifier.py     # Telegram通知器 - 发送通知
└── store.py        # 存储管理器 - 去重和持久化
```

### 模块职责

#### DMMonitor (monitor.py)
- 定期轮询Twitter DM API
- 管理监听服务的启停
- 处理API调用异常和重试

#### DMProcessor (processor.py)
- 解析Twitter私信数据结构
- 提取发送者信息和媒体附件
- 格式化消息内容为可读格式

#### TelegramNotifier (notifier.py)
- 发送格式化消息到Telegram
- 处理媒体文件转发
- 支持Markdown格式和错误恢复

#### DMStore (store.py)
- 记录已处理的私信ID
- JSON文件持久化存储
- 自动清理过期记录

## ⚙️ 配置说明

### 环境变量

```bash
# DM监听配置
ENABLE_DM_MONITORING=true           # 启用DM监听
DM_POLL_INTERVAL=60                 # 轮询间隔（秒）
DM_TARGET_CHAT_ID=123456789         # 接收通知的Telegram聊天ID
DM_STORE_FILE=data/processed_dm_ids.json  # 存储文件路径
DM_STORE_MAX_AGE_DAYS=7             # 记录保留天数
```

### 必需权限
- Twitter API需要 `read-write-directmessages` 权限
- 免费版API账户即可使用
- 需要正确配置所有Twitter API密钥

## 🔧 使用指南

### 1. 配置步骤

1. **获取Twitter API权限**
   ```bash
   # 确保您的Twitter Developer账户有DM权限
   # 在Twitter Developer Portal中申请read-write-directmessages权限
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑.env文件，设置DM相关配置
   ```

3. **获取Telegram聊天ID**
   ```bash
   # 方法1: 向@userinfobot发送消息获取ID
   # 方法2: 使用/start命令，查看日志中的user_id
   ```

### 2. 启动服务

```bash
# 正常启动（包含DM监听）
python main.py

# 或使用Docker
docker-compose up -d
```

### 3. 验证功能

1. **检查DM权限**
   - 启动时查看日志中的"Twitter DM API权限测试"
   - 使用 `/dm_status` 命令查看状态

2. **测试私信转发**
   - 让其他用户给您发送Twitter私信
   - 检查Telegram是否收到通知

## 📱 Telegram命令

### 新增命令

- `/dm_status` - 查看DM监听状态和配置
- `/help` - 更新了帮助信息，包含DM功能说明

### 通知格式

```
📩 Twitter私信通知

👤 发送者: @username (显示名称)
🕒 时间: 2025-07-20 14:30:25 UTC
💬 内容: [私信内容]

🔗 消息ID: 1234567890123456789
```

## 🛠️ 技术实现

### API调用流程
1. 使用Twitter API v2的 `GET /2/dm_events` 端点
2. 获取私信列表并解析响应数据
3. 提取用户信息和媒体附件
4. 通过Telegram Bot API发送通知

### 错误处理
- **频率限制**: 自动等待并重试
- **网络异常**: 指数退避重试策略
- **API权限**: 优雅降级和错误提示
- **数据解析**: 容错处理和默认值

### 性能优化
- **批量处理**: 一次API调用获取多条私信
- **增量更新**: 只处理新的私信
- **内存管理**: 及时清理临时数据
- **文件IO**: 异步写入和原子操作

## 🔍 监控和调试

### 日志信息
```bash
# 查看DM监听日志
tail -f logs/twitter-bot.log | grep -i "dm"

# 关键日志事件
- "DM监听器已启动"
- "发现 X 条新私信"
- "私信处理完成"
- "Twitter DM API权限测试成功"
```

### 常见问题

1. **私信不转发**
   - 检查DM_TARGET_CHAT_ID是否正确
   - 验证Twitter API权限
   - 查看错误日志

2. **重复通知**
   - 检查存储文件权限
   - 验证消息ID去重逻辑

3. **API限制**
   - 调整轮询间隔
   - 检查API使用量

## 📈 扩展功能

### 计划中的增强
- 双向私信（Telegram回复Twitter）
- 私信统计和分析
- 多用户支持
- 私信过滤规则
- 媒体文件缓存

### 自定义开发
代码采用模块化设计，便于扩展：
- 自定义消息格式化
- 添加新的通知渠道
- 集成其他社交平台
- 实现高级过滤功能

## 🔒 安全考虑

- 私信内容仅在本地处理，不上传第三方
- API密钥采用环境变量管理
- 支持Docker容器化部署
- 定期清理敏感数据

---

*该功能完全开源，遵循项目许可证。欢迎贡献代码和反馈问题！*