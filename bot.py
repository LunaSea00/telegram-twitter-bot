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
    
    def is_authorized_user(self, user_id: int) -> bool:
        return str(user_id) == self.authorized_user_id
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
            return
            
        await update.message.reply_text(
            "你好！发送任何消息给我，我会自动转发到你的Twitter账户。\n\n"
            "使用 /help 查看帮助信息。"
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
        """处理Twitter私信webhook"""
        try:
            # 获取签名
            signature = request.headers.get('x-twitter-webhooks-signature')
            if not signature:
                logger.warning("收到没有签名的webhook请求")
                return web.Response(status=401)
            
            # 读取请求体
            body = await request.read()
            
            # 验证签名
            if not self.verify_webhook_signature(body, signature):
                logger.warning("Webhook签名验证失败")
                return web.Response(status=401)
            
            # 解析JSON
            data = json.loads(body.decode('utf-8'))
            
            # 检查是否是私信事件
            if 'direct_message_events' in data:
                for dm_event in data['direct_message_events']:
                    # 确保不是自己发送的消息
                    sender_id = dm_event.get('message_create', {}).get('sender_id')
                    if sender_id != str(self.twitter_access_token).split('-')[0]:  # 简单检查
                        
                        # 获取发送者信息
                        users = data.get('users', {})
                        sender_info = users.get(sender_id, {})
                        sender_name = sender_info.get('name', 'Unknown')
                        sender_username = sender_info.get('screen_name', 'unknown')
                        
                        # 获取消息内容
                        message_data = dm_event.get('message_create', {}).get('message_data', {})
                        text = message_data.get('text', '')
                        
                        # 格式化消息
                        formatted_message = f"""
📩 <b>收到新私信</b>

👤 <b>发送者:</b> {sender_name} (@{sender_username})
💬 <b>内容:</b> {text}

🔗 <b>时间:</b> {dm_event.get('created_timestamp', 'Unknown')}
                        """.strip()
                        
                        # 发送到Telegram
                        await self.send_telegram_message(formatted_message)
                        logger.info(f"已转发私信到Telegram: 来自 @{sender_username}")
            
            return web.Response(text="OK")
            
        except Exception as e:
            logger.error(f"处理私信webhook时出错: {e}")
            return web.Response(status=500)
    
    async def webhook_challenge(self, request):
        """处理Twitter webhook验证挑战"""
        try:
            # 获取挑战码
            crc_token = request.query.get('crc_token')
            if not crc_token or not self.webhook_secret:
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
        
        # 发送启动通知
        await self.send_startup_notification()
        
        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
        finally:
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