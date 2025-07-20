import logging
from typing import Dict, Any, Optional
from ..utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram通知器 - 负责发送私信通知到Telegram"""
    
    def __init__(self, telegram_bot, config):
        self.telegram_bot = telegram_bot
        self.config = config
        self.target_chat_id = getattr(config, 'dm_target_chat_id', None)
        
        # 验证配置
        if not self.target_chat_id:
            logger.warning("未设置DM_TARGET_CHAT_ID，私信通知可能无法正常工作")
    
    async def send_dm_notification(self, formatted_message: str, message_data: Dict[str, Any]):
        """发送私信通知到Telegram"""
        try:
            if not self.target_chat_id:
                logger.error("未设置目标聊天ID，无法发送私信通知")
                return False
            
            # 发送文本消息
            await self._send_text_message(formatted_message)
            
            # 如果有媒体，尝试发送媒体
            media = message_data.get('media', [])
            if media:
                await self._send_media_messages(media)
            
            logger.info(f"私信通知发送成功: {message_data['id']}")
            return True
            
        except Exception as e:
            ErrorHandler.log_error(e, f"发送私信通知 {message_data.get('id', 'unknown')}")
            return False
    
    async def _send_text_message(self, text: str):
        """发送文本消息"""
        try:
            # 获取bot实例
            if not self.telegram_bot.application or not self.telegram_bot.application.bot:
                logger.error("Telegram bot未初始化")
                return
            
            bot = self.telegram_bot.application.bot
            
            # 发送消息
            await bot.send_message(
                chat_id=self.target_chat_id,
                text=text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.debug("文本私信通知发送成功")
            
        except Exception as e:
            logger.error(f"发送文本消息失败: {e}")
            # 如果Markdown格式失败，尝试普通文本
            try:
                bot = self.telegram_bot.application.bot
                await bot.send_message(
                    chat_id=self.target_chat_id,
                    text=text,
                    disable_web_page_preview=True
                )
                logger.info("使用普通文本格式重新发送成功")
            except Exception as e2:
                logger.error(f"普通文本发送也失败: {e2}")
                raise
    
    async def _send_media_messages(self, media_list: list):
        """发送媒体消息"""
        try:
            if not media_list:
                return
            
            bot = self.telegram_bot.application.bot
            
            for media in media_list:
                media_type = media.get('type', '').lower()
                media_url = media.get('url') or media.get('preview_image_url')
                
                if not media_url:
                    logger.warning(f"媒体没有可用的URL: {media}")
                    continue
                
                try:
                    if media_type in ['photo', 'image']:
                        await bot.send_photo(
                            chat_id=self.target_chat_id,
                            photo=media_url,
                            caption=f"📎 来自Twitter私信的图片"
                        )
                    elif media_type in ['video']:
                        await bot.send_video(
                            chat_id=self.target_chat_id,
                            video=media_url,
                            caption=f"📎 来自Twitter私信的视频"
                        )
                    elif media_type in ['animated_gif', 'gif']:
                        await bot.send_animation(
                            chat_id=self.target_chat_id,
                            animation=media_url,
                            caption=f"📎 来自Twitter私信的GIF"
                        )
                    else:
                        # 对于其他类型，发送链接
                        await bot.send_message(
                            chat_id=self.target_chat_id,
                            text=f"📎 媒体文件 ({media_type}): {media_url}"
                        )
                    
                    logger.debug(f"媒体发送成功: {media_type}")
                    
                except Exception as e:
                    logger.warning(f"发送媒体失败: {e}")
                    # 如果媒体发送失败，发送链接
                    try:
                        await bot.send_message(
                            chat_id=self.target_chat_id,
                            text=f"📎 媒体文件链接 ({media_type}): {media_url}"
                        )
                    except Exception as e2:
                        logger.error(f"发送媒体链接也失败: {e2}")
            
        except Exception as e:
            logger.error(f"发送媒体消息失败: {e}")
    
    async def send_dm_status(self, status_info: Dict[str, Any]):
        """发送私信监听状态信息"""
        try:
            if not self.target_chat_id:
                return
            
            status_text = f"""🔍 **私信监听状态**

📊 **运行状态**: {'✅ 运行中' if status_info.get('running') else '❌ 已停止'}
⚙️ **监听启用**: {'✅ 是' if status_info.get('enabled') else '❌ 否'}
⏱️ **轮询间隔**: {status_info.get('poll_interval', 'unknown')}秒
📈 **已处理**: {status_info.get('processed_count', 0)}条私信
🕒 **最后检查**: {status_info.get('last_check', 'unknown')}"""
            
            await self._send_text_message(status_text)
            
        except Exception as e:
            ErrorHandler.log_error(e, "发送DM状态信息")
    
    def validate_config(self) -> bool:
        """验证配置是否正确"""
        if not self.target_chat_id:
            logger.error("DM_TARGET_CHAT_ID未配置")
            return False
        
        try:
            # 验证chat_id格式
            int(self.target_chat_id)
            return True
        except ValueError:
            logger.error("DM_TARGET_CHAT_ID格式无效，必须是数字")
            return False