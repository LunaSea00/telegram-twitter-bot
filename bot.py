import os
import logging
import tweepy
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
        self.authorized_user_id = os.getenv('AUTHORIZED_USER_ID')
        
        if not all([self.telegram_token, self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_token_secret, 
                   self.twitter_bearer_token, self.authorized_user_id]):
            raise ValueError("Missing required environment variables")
        
        self.twitter_client = tweepy.Client(
            bearer_token=self.twitter_bearer_token,
            consumer_key=self.twitter_api_key,
            consumer_secret=self.twitter_api_secret,
            access_token=self.twitter_access_token,
            access_token_secret=self.twitter_access_token_secret,
            wait_on_rate_limit=True
        )
    
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
        2. /start - 开始使用
        3. /help - 显示帮助信息
        
        注意：消息长度不能超过280字符
        """
        await update.message.reply_text(help_text)
    
    async def tweet_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized_user(update.effective_user.id):
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
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
            await update.message.reply_text(f"❌ 发送推文失败: {str(e)}")
    
    async def run(self):
        # 设置Telegram bot
        application = Application.builder().token(self.telegram_token).build()
        
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.tweet_message))
        
        # 设置健康检查服务器
        async def health_check(request):
            return web.Response(text="OK", status=200)
        
        app = web.Application()
        app.router.add_get("/health", health_check)
        app.router.add_get("/", health_check)
        
        # 启动HTTP服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        
        logger.info("健康检查服务器启动在端口8000...")
        logger.info("Bot开始运行...")
        
        # 启动Telegram bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            await runner.cleanup()

if __name__ == "__main__":
    bot = TwitterBot()
    asyncio.run(bot.run())