import os
import logging
import tweepy
import asyncio
import aiohttp
import requests
import tempfile
import hmac
import hashlib
import base64
import json
from datetime import datetime
from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
from src.dm.manager import DMManager

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TwitterBot:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.twitter_client_id = os.getenv('TWITTER_CLIENT_ID')
        self.twitter_client_secret = os.getenv('TWITTER_CLIENT_SECRET')
        self.authorized_user_id = os.getenv('AUTHORIZED_USER_ID')
        self.app_url = os.getenv('APP_URL')  # 添加应用URL环境变量
        self.webhook_secret = os.getenv('TWITTER_WEBHOOK_SECRET')  # 添加webhook密钥
        
        # 私信功能管理器
        self.dm_manager = None
        
        if not all([self.telegram_token, self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_token_secret, 
                   self.twitter_bearer_token, self.authorized_user_id]):
            raise ValueError("Missing required environment variables")
        
        # 初始化Twitter客户端，但不在启动时测试连接
        try:
            self.twitter_client = tweepy.Client(
                bearer_token=self.twitter_bearer_token,
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret,
                wait_on_rate_limit=True
            )
            logger.info("Twitter客户端初始化成功")
        except Exception as e:
            logger.error(f"Twitter客户端初始化失败: {e}")
            self.twitter_client = None
            
        # 初始化DM配置对象
        self.dm_config = self._create_dm_config()
    
    def is_authorized_user(self, user_id: int) -> bool:
        return str(user_id) == self.authorized_user_id
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
            
        await update.message.reply_text(
            "你好！发送任何消息给我，我会自动转发到你的Twitter账户。\n\n"
            "使用 /help 查看帮助信息。\n"
            "使用 /dm 启用私信监听功能。"
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
            
        help_text = """
        使用方法：
        1. 直接发送文本消息 - 将会发布到Twitter
        2. 发送图片（可带文字描述） - 将会发布图片到Twitter
        3. /start - 开始使用
        4. /help - 显示帮助信息
        5. /dm - 启用/查看私信监听功能
        6. /status - 查看Bot运行状态
        
        注意：消息长度不能超过280字符，图片将自动压缩优化
        """
        await update.message.reply_text(help_text)
    
    async def tweet_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
        
        if not self.twitter_client:
            await update.message.reply_text("❌ Twitter API未正确配置，请检查环境变量。")
            return
            
        try:
            message_text = update.message.text
            
            if len(message_text) > 280:
                await update.message.reply_text("消息太长了！Twitter限制280字符以内。")
                return
            
            response = self.twitter_client.create_tweet(text=message_text)
            tweet_id = response.data['id']
            
            await update.message.reply_text(
                f"✅ 推文发送成功！\n\n"
                f"推文ID: {tweet_id}\n"
                f"内容: {message_text}"
            )
            
        except Exception as e:
            logger.error(f"发送推文时出错: {e}")
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                await update.message.reply_text("❌ Twitter API认证失败，请检查API密钥和权限设置。")
            else:
                await update.message.reply_text(f"❌ 发送推文失败: {error_msg}")
    
    async def tweet_with_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
        
        if not self.twitter_client:
            await update.message.reply_text("❌ Twitter API未正确配置，请检查环境变量。")
            return
            
        try:
            # 获取图片和文字描述
            photo = update.message.photo[-1]  # 获取最大尺寸的图片
            caption = update.message.caption or ""
            
            if len(caption) > 280:
                await update.message.reply_text("文字描述太长了！Twitter限制280字符以内。")
                return
            
            # 下载图片
            file = await context.bot.get_file(photo.file_id)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                # 下载图片到临时文件
                await file.download_to_drive(temp_file.name)
                
                try:
                    # 使用Pillow优化图片
                    with Image.open(temp_file.name) as img:
                        # 转换为RGB（Twitter需要）
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # 调整图片大小（Twitter限制5MB）
                        max_size = (2048, 2048)
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        
                        # 保存优化后的图片
                        optimized_path = temp_file.name.replace('.jpg', '_optimized.jpg')
                        img.save(optimized_path, 'JPEG', quality=85, optimize=True)
                    
                    # 初始化Twitter API v1.1客户端用于媒体上传
                    auth = tweepy.OAuth1UserHandler(
                        self.twitter_api_key,
                        self.twitter_api_secret,
                        self.twitter_access_token,
                        self.twitter_access_token_secret
                    )
                    api = tweepy.API(auth)
                    
                    # 上传媒体
                    media = api.media_upload(optimized_path)
                    
                    # 创建带媒体的推文
                    response = self.twitter_client.create_tweet(
                        text=caption,
                        media_ids=[media.media_id]
                    )
                    
                    tweet_id = response.data['id']
                    
                    await update.message.reply_text(
                        f"✅ 图片推文发送成功！\n\n"
                        f"推文ID: {tweet_id}\n"
                        f"描述: {caption if caption else '无描述'}"
                    )
                    
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_file.name)
                        if 'optimized_path' in locals():
                            os.unlink(optimized_path)
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"发送图片推文时出错: {e}")
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                await update.message.reply_text("❌ Twitter API认证失败，请检查API密钥和权限设置。")
            elif "413" in error_msg or "too large" in error_msg.lower():
                await update.message.reply_text("❌ 图片太大，请发送较小的图片。")
            else:
                await update.message.reply_text(f"❌ 发送图片推文失败: {error_msg}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证Twitter webhook签名"""
        if not self.webhook_secret:
            logger.warning("未webhook密钥未设置，跳过签名验证")
            return False
            
        try:
            # Twitter使用sha256 HMAC
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            
            # Twitter发送的签名是base64编码的
            expected_signature_b64 = base64.b64encode(expected_signature).decode('utf-8')
            
            # 比较签名（常量时间比较，防止时间攻击）
            return hmac.compare_digest(signature, expected_signature_b64)
        except Exception as e:
            logger.error(f"验证webhook签名时出错: {e}")
            return False
    
    async def send_startup_notification(self):
        """发送启动通知给授权用户"""
        try:
            application = Application.builder().token(self.telegram_token).build()
            startup_message = f"""
🤖 <b>Twitter Bot 已启动</b>

✅ <b>状态:</b> 在线运行
🔗 <b>Twitter API:</b> 已连接
⏰ <b>启动时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 发送任何消息给我，我会自动转发到你的Twitter账户。
使用 /status 查看运行状态。
            """.strip()
            
            await application.bot.send_message(
                chat_id=self.authorized_user_id,
                text=startup_message,
                parse_mode='HTML'
            )
            logger.info("启动通知已发送")
        except Exception as e:
            logger.error(f"发送启动通知失败: {e}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示机器人状态"""
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
        
        try:
            # 检查Twitter API连接
            twitter_status = "✅ 正常" if self.twitter_client else "❌ 失败"
            
            # 获取运行时间（简化版）
            uptime = "运行中"
            
            status_message = f"""
📊 <b>Bot 运行状态</b>

🤖 <b>Telegram Bot:</b> ✅ 在线
🐦 <b>Twitter API:</b> {twitter_status}
⏱️ <b>运行状态:</b> {uptime}
👤 <b>授权用户:</b> {update.effective_user.first_name}

💡 <b>使用提示:</b>
• 直接发送文本 → 发布推文
• 发送图片 → 发布图片推文
• /help → 查看帮助
            """.strip()
            
            await update.message.reply_text(status_message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"获取状态时出错: {e}")
            await update.message.reply_text("❌ 获取状态失败")
    
    def _create_dm_config(self):
        """创建DM配置对象"""
        class DMConfig:
            def __init__(self):
                self.enable_dm_monitoring = os.getenv('ENABLE_DM_MONITORING', 'false').lower() == 'true'
                self.dm_poll_interval = int(os.getenv('DM_POLL_INTERVAL', '60'))
                self.dm_target_chat_id = os.getenv('DM_TARGET_CHAT_ID', os.getenv('AUTHORIZED_USER_ID'))
                self.dm_store_file = os.getenv('DM_STORE_FILE', 'data/processed_dm_ids.json')
                self.dm_store_max_age_days = int(os.getenv('DM_STORE_MAX_AGE_DAYS', '7'))
        
        return DMConfig()
    
    async def dm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理/dm命令 - 启用或查看私信功能状态"""
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
        
        try:
            # 如果DM管理器未初始化，先初始化
            if not self.dm_manager:
                await self._initialize_dm_manager()
            
            # 尝试唤醒DM功能
            result = await self.dm_manager.wake_up()
            
            status_emoji = {
                'success': '✅',
                'error': '❌', 
                'info': 'ℹ️'
            }.get(result['status'], '❓')
            
            response_text = f"{status_emoji} {result['message']}"
            
            # 如果成功启动，显示详细状态
            if result['status'] == 'success':
                dm_status = self.dm_manager.get_status()
                response_text += f"\n\n📊 **私信监听状态**\n"
                response_text += f"🔄 轮询间隔: {dm_status.get('poll_interval', 'N/A')}秒\n"
                response_text += f"📱 目标聊天: {self.dm_config.dm_target_chat_id}\n"
                response_text += f"💾 已处理: {dm_status.get('processed_count', 0)}条私信"
            
            await update.message.reply_text(response_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"处理/dm命令时出错: {e}")
            await update.message.reply_text(f"❌ 处理DM命令失败: {str(e)}")
    
    async def _initialize_dm_manager(self):
        """初始化DM管理器"""
        try:
            if not self.dm_manager:
                self.dm_manager = DMManager(
                    twitter_client=self.twitter_client,
                    telegram_bot=self,
                    config=self.dm_config
                )
                
            # 如果未初始化，进行初始化（但不启动）
            if not self.dm_manager.is_initialized:
                await self.dm_manager.initialize()
                logger.info("DM管理器初始化完成")
                
        except Exception as e:
            logger.error(f"初始化DM管理器失败: {e}")
            raise

    async def send_telegram_message(self, message: str):
        """发送消息到Telegram"""
        try:
            application = Application.builder().token(self.telegram_token).build()
            await application.bot.send_message(
                chat_id=self.authorized_user_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"发送Telegram消息失败: {e}")
    
    async def handle_dm_webhook(self, request):
        """处理Twitter私信webhook - 会在DM功能可用时委托给DM管理器"""
        try:
            # 如果DM管理器可用，优先使用新的处理方式
            if self.dm_manager and self.dm_manager.is_initialized:
                logger.info("使用DM管理器处理webhook")
                # 这里可以实现更高级的webhook处理逻辑
                # 目前简单返回OK
                return web.Response(text="OK")
            
            # 备用方案：简化的webhook处理（无签名验证）
            try:
                body = await request.read()
                data = json.loads(body.decode('utf-8'))
                
                # 检查是否是私信事件
                if 'direct_message_events' in data:
                    for dm_event in data['direct_message_events']:
                        sender_id = dm_event.get('message_create', {}).get('sender_id')
                        if sender_id and sender_id != str(self.twitter_access_token).split('-')[0]:
                            
                            # 获取基本信息
                            users = data.get('users', {})
                            sender_info = users.get(sender_id, {})
                            sender_name = sender_info.get('name', 'Unknown')
                            sender_username = sender_info.get('screen_name', 'unknown')
                            
                            message_data = dm_event.get('message_create', {}).get('message_data', {})
                            text = message_data.get('text', '')
                            
                            # 简化的消息格式
                            simple_message = f"📩 新私信\n发送者: {sender_name} (@{sender_username})\n内容: {text}"
                            
                            await self.send_telegram_message(simple_message)
                            logger.info(f"简化模式转发私信: @{sender_username}")
                
                return web.Response(text="OK")
                
            except Exception as e:
                logger.warning(f"简化webhook处理失败: {e}")
                return web.Response(text="OK")  # 仍然返回OK以免影响其他功能
            
        except Exception as e:
            logger.error(f"处理webhook时出错: {e}")
            return web.Response(status=500)
    
    async def webhook_challenge(self, request):
        """处理Twitter webhook验证挑战"""
        try:
            crc_token = request.query.get('crc_token')
            if not crc_token:
                logger.warning("未提供crc_token")
                return web.Response(status=400)
            
            if not self.webhook_secret:
                logger.warning("webhook密钥未设置，无法处理挑战")
                return web.Response(status=400)
            
            # 生成响应
            signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                crc_token.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            response_token = base64.b64encode(signature).decode('utf-8')
            
            return web.json_response({
                'response_token': f'sha256={response_token}'
            })
            
        except Exception as e:
            logger.error(f"处理webhook挑战时出错: {e}")
            return web.Response(status=500)
    
    async def keep_alive(self):
        """自动保活任务，每14分钟ping一次健康检查端点"""
        if not self.app_url:
            logger.info("未设置APP_URL，跳过自动保活")
            return
            
        while True:
            try:
                await asyncio.sleep(14 * 60)  # 14分钟
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.app_url}/health") as response:
                        if response.status == 200:
                            logger.info("保活ping成功")
                        else:
                            logger.warning(f"保活ping失败，状态码: {response.status}")
            except Exception as e:
                logger.error(f"保活ping出错: {e}")
            except asyncio.CancelledError:
                break
    
    async def run(self):
        # 设置Telegram bot
        application = Application.builder().token(self.telegram_token).build()
        
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("dm", self.dm_command))
        application.add_handler(MessageHandler(filters.PHOTO, self.tweet_with_image))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tweet_message))
        
        # 设置健康检查服务器
        async def health_check(request):
            return web.Response(text="OK", status=200)
        
        app = web.Application()
        app.router.add_get("/health", health_check)
        app.router.add_get("/", health_check)
        app.router.add_get("/webhook/twitter", self.webhook_challenge)  # Twitter webhook验证
        app.router.add_post("/webhook/twitter", self.handle_dm_webhook)  # Twitter私信webhook
        
        # 启动HTTP服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        
        logger.info("健康检查服务器启动在端口8000...")
        logger.info("Bot开始运行...")
        
        # 启动自动保活任务
        keep_alive_task = None
        if self.app_url:
            keep_alive_task = asyncio.create_task(self.keep_alive())
            logger.info("自动保活任务已启动")
        
        # 启动Telegram bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # 初始化私信功能（但不启动监听）
        try:
            await self._initialize_dm_manager()
            logger.info("私信功能初始化完成")
        except Exception as e:
            logger.warning(f"私信功能初始化失败，将在需要时重试: {e}")
        
        # 发送启动通知
        await self.send_startup_notification()
        
        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
        finally:
            # 停止私信功能
            if self.dm_manager:
                try:
                    await self.dm_manager.stop()
                    logger.info("私信功能已停止")
                except Exception as e:
                    logger.error(f"停止私信功能时出错: {e}")
            
            if keep_alive_task:
                keep_alive_task.cancel()
                try:
                    await keep_alive_task
                except asyncio.CancelledError:
                    pass
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            await runner.cleanup()

if __name__ == "__main__":
    bot = TwitterBot()
    asyncio.run(bot.run())