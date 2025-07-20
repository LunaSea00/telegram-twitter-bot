import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, handlers):
        self.token = token
        self.handlers = handlers
        self.application = None
    
    def setup_handlers(self):
        """设置命令和消息处理器"""
        # 命令处理器
        self.application.add_handler(CommandHandler("start", self.handlers.start))
        self.application.add_handler(CommandHandler("help", self.handlers.help))
        self.application.add_handler(CommandHandler("status", self.handlers.status))
        self.application.add_handler(CommandHandler("stats", self.handlers.stats))
        self.application.add_handler(CommandHandler("dm_status", self.handlers.dm_status))
        
        # 消息处理器（处理非命令的文本消息，包括私信）
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message)
        )
        
        # 图片和文档处理器
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.handlers.handle_photo)
        )
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self.handlers.handle_document)
        )
        
        # 全局错误处理器
        self.application.add_error_handler(self.handlers.error_handler)
        
        logger.info("已注册所有处理器")
    
    async def initialize(self):
        """初始化Telegram机器人"""
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            await self.application.initialize()
            logger.info("Telegram机器人初始化成功")
        except Exception as e:
            logger.error(f"Telegram机器人初始化失败: {e}")
            raise
    
    async def start_polling(self):
        """开始轮询消息"""
        try:
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True,  # 跳过待处理的更新
                read_timeout=30,            # 读取超时时间
                write_timeout=30,           # 写入超时时间
                connect_timeout=30,         # 连接超时时间
                pool_timeout=30             # 连接池超时时间
            )
            logger.info("Telegram机器人开始轮询")
        except Exception as e:
            logger.error(f"启动轮询失败: {e}")
            raise
    
    async def stop(self):
        """停止机器人"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram机器人已停止")
        except Exception as e:
            logger.error(f"停止机器人时出错: {e}")
    
    def get_bot_info(self):
        """获取机器人信息"""
        if self.application and self.application.bot:
            return {
                'username': self.application.bot.username,
                'first_name': self.application.bot.first_name,
                'can_join_groups': self.application.bot.can_join_groups,
                'can_read_all_group_messages': self.application.bot.can_read_all_group_messages,
                'supports_inline_queries': self.application.bot.supports_inline_queries
            }
        return None