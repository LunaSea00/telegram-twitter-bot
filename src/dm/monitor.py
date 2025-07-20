import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from ..utils.exceptions import TwitterAPIError
from ..utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class DMMonitor:
    """Twitter私信监听器"""
    
    def __init__(self, twitter_client, dm_processor, dm_store, config):
        self.twitter_client = twitter_client
        self.dm_processor = dm_processor
        self.dm_store = dm_store
        self.config = config
        self.is_running = False
        self.poll_interval = getattr(config, 'dm_poll_interval', 60)
        self.enable_monitoring = getattr(config, 'enable_dm_monitoring', True)
        
    async def start_monitoring(self):
        """开始监听私信"""
        if not self.enable_monitoring:
            logger.info("私信监听功能已禁用")
            return
            
        if self.is_running:
            logger.warning("私信监听器已在运行")
            return
            
        self.is_running = True
        logger.info(f"🔍 开始监听Twitter私信，轮询间隔: {self.poll_interval}秒")
        
        while self.is_running:
            try:
                await self._check_new_messages()
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                logger.info("私信监听被取消")
                break
            except Exception as e:
                ErrorHandler.log_error(e, "私信监听")
                # 错误后等待更长时间再重试
                await asyncio.sleep(min(self.poll_interval * 2, 300))
    
    async def stop_monitoring(self):
        """停止监听私信"""
        if self.is_running:
            self.is_running = False
            logger.info("🛑 私信监听器已停止")
    
    async def _check_new_messages(self):
        """检查新私信"""
        try:
            # 获取最新私信
            messages = await self.twitter_client.get_direct_messages()
            
            if not messages:
                logger.debug("没有新的私信")
                return
            
            # 处理新消息
            new_messages = []
            for message in messages:
                message_id = message.get('id')
                if message_id and not self.dm_store.is_processed(message_id):
                    new_messages.append(message)
            
            if new_messages:
                logger.info(f"📥 发现 {len(new_messages)} 条新私信")
                await self._process_new_messages(new_messages)
            else:
                logger.debug("没有新的私信需要处理")
                
        except TwitterAPIError as e:
            logger.error(f"获取私信时出错: {e}")
        except Exception as e:
            ErrorHandler.log_error(e, "检查新私信")
    
    async def _process_new_messages(self, messages: List[Dict[str, Any]]):
        """处理新私信"""
        for message in messages:
            try:
                message_id = message.get('id')
                if not message_id:
                    continue
                
                # 处理消息并发送到Telegram
                await self.dm_processor.process_message(message)
                
                # 标记为已处理
                self.dm_store.mark_processed(message_id)
                
                logger.info(f"✅ 私信 {message_id} 处理完成")
                
            except Exception as e:
                ErrorHandler.log_error(e, f"处理私信 {message.get('id', 'unknown')}")
                continue
    
    def get_status(self) -> Dict[str, Any]:
        """获取监听器状态"""
        return {
            'running': self.is_running,
            'enabled': self.enable_monitoring,
            'poll_interval': self.poll_interval,
            'processed_count': self.dm_store.get_processed_count(),
            'last_check': datetime.now(timezone.utc).isoformat()
        }