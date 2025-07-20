import asyncio
import logging
import signal
import sys
import os
from src.config.settings import get_config
from src.twitter.client import TwitterClient
from src.telegram.bot import TelegramBot
from src.telegram.handlers import TelegramHandlers
from src.auth.service import AuthService
from src.utils.logger import setup_logging
from src.utils.health_server import HealthServer
from src.utils.exceptions import ConfigurationError, TwitterAPIError
from src.utils.error_handler import ErrorHandler
from src.dm.monitor import DMMonitor
from src.dm.processor import DMProcessor
from src.dm.notifier import TelegramNotifier
from src.dm.store import DMStore

class TwitterBot:
    def __init__(self):
        self.config = None
        self.twitter_client = None
        self.auth_service = None
        self.handlers = None
        self.telegram_bot = None
        self.health_server = None
        self.logger = None
        self._running = False
        
        # DM监听相关组件
        self.dm_store = None
        self.dm_notifier = None
        self.dm_processor = None
        self.dm_monitor = None
        self.dm_monitor_task = None
    
    async def initialize(self):
        """初始化所有组件"""
        try:
            # 加载配置
            self.config = get_config()
            
            # 设置日志
            log_file = "logs/twitter-bot.log" if not os.getenv("DOCKER") else None
            self.logger = setup_logging(
                log_level=self.config.log_level,
                log_file=log_file
            )
            self.logger.info("🚀 开始初始化Twitter Bot...")
            self.logger.info("✅ 配置加载成功")
            
            # 初始化服务
            self.twitter_client = TwitterClient(
                self.config.twitter_credentials, 
                self.config.tweet_max_length
            )
            self.auth_service = AuthService(self.config.authorized_user_id)
            self.handlers = TelegramHandlers(
                self.twitter_client, 
                self.auth_service, 
                self.config
            )
            self.telegram_bot = TelegramBot(self.config.telegram_token, self.handlers)
            self.health_server = HealthServer(self.config.health_port)
            
            # 初始化DM监听组件
            if self.config.enable_dm_monitoring:
                self.dm_store = DMStore(self.config)
                self.dm_notifier = TelegramNotifier(self.telegram_bot, self.config)
                self.dm_processor = DMProcessor(self.dm_notifier, self.config)
                self.dm_monitor = DMMonitor(
                    self.twitter_client, 
                    self.dm_processor, 
                    self.dm_store, 
                    self.config
                )
                self.logger.info("✅ DM监听组件初始化成功")
            else:
                self.logger.info("🔕 DM监听功能已禁用")
            
            self.logger.info("✅ 所有组件初始化成功")
            
        except ConfigurationError as e:
            self.logger.error(f"❌ 配置错误: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"❌ 初始化失败: {e}")
            sys.exit(1)
    
    async def start(self):
        """启动机器人"""
        try:
            await self.initialize()
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 启动健康检查服务器
            await self.health_server.start()
            
            # 初始化并启动Telegram机器人
            await self.telegram_bot.initialize()
            
            # 测试Twitter连接
            if await self.twitter_client.test_connection():
                self.logger.info("✅ Twitter连接测试成功")
            else:
                self.logger.warning("⚠️ Twitter连接测试失败，但将继续运行")
            
            # 测试DM API权限（如果启用）
            if self.dm_monitor:
                if await self.twitter_client.test_dm_access():
                    self.logger.info("✅ Twitter DM API权限测试成功")
                else:
                    self.logger.warning("⚠️ Twitter DM API权限测试失败，DM监听可能无法正常工作")
            
            # 获取机器人信息
            bot_info = self.telegram_bot.get_bot_info()
            if bot_info:
                self.logger.info(f"🤖 机器人信息: @{bot_info['username']}")
            
            # 开始轮询
            await self.telegram_bot.start_polling()
            self._running = True
            
            # 启动DM监听（如果启用）
            if self.dm_monitor:
                self.dm_monitor_task = asyncio.create_task(self.dm_monitor.start_monitoring())
                self.logger.info("🔍 DM监听器已启动")
            
            self.logger.info("🎉 TwitterBot 启动成功！")
            self.logger.info(f"🔗 健康检查: http://localhost:{self.config.health_port}/health")
            
            if self.dm_monitor:
                self.logger.info("📩 DM监听功能已启用，将监听Twitter私信并转发到Telegram")
            
            # 保持运行
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            self.logger.info("👋 收到停止信号...")
        except Exception as e:
            ErrorHandler.log_error(e, "启动机器人")
            sys.exit(1)
        finally:
            await self.stop()
    
    async def stop(self):
        """停止机器人"""
        if not self._running:
            return
            
        self.logger.info("🛑 正在停止机器人...")
        
        try:
            # 停止DM监听
            if self.dm_monitor:
                await self.dm_monitor.stop_monitoring()
            
            if self.dm_monitor_task and not self.dm_monitor_task.done():
                self.dm_monitor_task.cancel()
                try:
                    await self.dm_monitor_task
                except asyncio.CancelledError:
                    pass
            
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            if self.health_server:
                await self.health_server.stop()
            
            self._running = False
            self.logger.info("✅ 机器人已停止")
            
        except Exception as e:
            ErrorHandler.log_error(e, "停止机器人")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """主函数"""
    bot = TwitterBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)