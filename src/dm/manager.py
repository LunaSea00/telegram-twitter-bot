import asyncio
import logging
from typing import Optional, Dict, Any
from .monitor import DMMonitor
from .processor import DMProcessor
from .notifier import TelegramNotifier
from .store import DMStore
from ..utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class DMManager:
    """私信功能管理器 - 提供隔离的私信功能"""
    
    def __init__(self, twitter_client=None, telegram_bot=None, config=None):
        self.twitter_client = twitter_client
        self.telegram_bot = telegram_bot
        self.config = config
        
        # 组件实例
        self.dm_store = None
        self.telegram_notifier = None
        self.dm_processor = None
        self.dm_monitor = None
        
        # 运行状态
        self.is_initialized = False
        self.is_running = False
        self.initialization_error = None
        
    async def initialize(self) -> bool:
        """初始化私信功能组件"""
        try:
            logger.info("🔄 正在初始化私信功能...")
            
            # 验证必要依赖
            if not self._validate_dependencies():
                self.initialization_error = "缺少必要的依赖"
                return False
            
            # 初始化组件
            self.dm_store = DMStore(self.config)
            self.telegram_notifier = TelegramNotifier(self.telegram_bot, self.config)
            self.dm_processor = DMProcessor(self.telegram_notifier, self.config)
            self.dm_monitor = DMMonitor(
                self.twitter_client, 
                self.dm_processor, 
                self.dm_store, 
                self.config
            )
            
            # 验证配置
            if not self.telegram_notifier.validate_config():
                self.initialization_error = "Telegram配置验证失败"
                return False
            
            # 测试Twitter API连接
            await self._test_twitter_dm_api()
            
            self.is_initialized = True
            logger.info("✅ 私信功能初始化成功")
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            ErrorHandler.log_error(e, "初始化私信功能")
            logger.error("❌ 私信功能初始化失败")
            return False
    
    def _validate_dependencies(self) -> bool:
        """验证依赖项"""
        if not self.config:
            logger.error("缺少配置对象")
            return False
        
        if not self.telegram_bot:
            logger.error("缺少Telegram Bot实例")
            return False
        
        # Twitter客户端可以为空，后续可以重新设置
        return True
    
    async def _test_twitter_dm_api(self):
        """测试Twitter DM API权限"""
        if not self.twitter_client:
            logger.warning("Twitter客户端未设置，跳过API测试")
            return
        
        try:
            # 尝试获取私信权限
            await self.twitter_client.get_direct_messages(max_results=1)
            logger.info("✅ Twitter DM API权限测试成功")
        except Exception as e:
            logger.warning(f"⚠️ Twitter DM API测试失败: {e}")
            # 不抛出异常，允许功能降级运行
    
    async def start(self) -> bool:
        """启动私信监听功能"""
        try:
            if not self.is_initialized:
                logger.error("私信功能未初始化，无法启动")
                return False
            
            if self.is_running:
                logger.warning("私信功能已在运行")
                return True
            
            if not self.twitter_client:
                logger.error("Twitter客户端未设置，无法启动私信监听")
                return False
            
            # 启动监听
            self.monitor_task = asyncio.create_task(self.dm_monitor.start_monitoring())
            self.is_running = True
            
            logger.info("🚀 私信监听已启动")
            return True
            
        except Exception as e:
            ErrorHandler.log_error(e, "启动私信功能")
            return False
    
    async def stop(self):
        """停止私信监听功能"""
        try:
            if not self.is_running:
                return
            
            if self.dm_monitor:
                await self.dm_monitor.stop_monitoring()
            
            if hasattr(self, 'monitor_task'):
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            logger.info("🛑 私信监听已停止")
            
        except Exception as e:
            ErrorHandler.log_error(e, "停止私信功能")
    
    def get_status(self) -> Dict[str, Any]:
        """获取私信功能状态"""
        status = {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'initialization_error': self.initialization_error,
            'twitter_client_available': self.twitter_client is not None,
            'telegram_bot_available': self.telegram_bot is not None
        }
        
        if self.is_initialized and self.dm_monitor:
            monitor_status = self.dm_monitor.get_status()
            status.update(monitor_status)
        
        return status
    
    async def send_status_notification(self):
        """发送状态通知到Telegram"""
        try:
            if not self.is_initialized or not self.telegram_notifier:
                return
            
            status = self.get_status()
            await self.telegram_notifier.send_dm_status(status)
            
        except Exception as e:
            ErrorHandler.log_error(e, "发送状态通知")
    
    def set_twitter_client(self, twitter_client):
        """设置Twitter客户端"""
        self.twitter_client = twitter_client
        if self.dm_monitor:
            self.dm_monitor.twitter_client = twitter_client
        logger.info("Twitter客户端已更新")
    
    def set_telegram_bot(self, telegram_bot):
        """设置Telegram Bot"""
        self.telegram_bot = telegram_bot
        if self.telegram_notifier:
            self.telegram_notifier.telegram_bot = telegram_bot
        logger.info("Telegram Bot已更新")
    
    async def wake_up(self) -> Dict[str, str]:
        """唤醒私信功能（用于/DM命令）"""
        try:
            if not self.is_initialized:
                # 尝试重新初始化
                success = await self.initialize()
                if not success:
                    return {
                        'status': 'error',
                        'message': f'初始化失败: {self.initialization_error}'
                    }
            
            if not self.is_running:
                # 尝试启动
                success = await self.start()
                if not success:
                    return {
                        'status': 'error',
                        'message': '启动私信监听失败'
                    }
                return {
                    'status': 'success',
                    'message': '私信功能已成功启动'
                }
            else:
                return {
                    'status': 'info',
                    'message': '私信功能已在运行中'
                }
                
        except Exception as e:
            ErrorHandler.log_error(e, "唤醒私信功能")
            return {
                'status': 'error',
                'message': f'唤醒失败: {str(e)}'
            }