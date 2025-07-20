import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from ..utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class DMProcessor:
    """私信处理器 - 负责格式化私信内容"""
    
    def __init__(self, telegram_notifier, config):
        self.telegram_notifier = telegram_notifier
        self.config = config
        self.target_chat_id = getattr(config, 'dm_target_chat_id', None)
        
    async def process_message(self, message: Dict[str, Any]):
        """处理单条私信"""
        try:
            # 解析消息内容
            message_data = self._parse_message(message)
            
            if not message_data:
                logger.warning(f"无法解析私信: {message.get('id', 'unknown')}")
                return
            
            # 格式化消息
            formatted_message = self._format_message(message_data)
            
            # 发送到Telegram
            await self.telegram_notifier.send_dm_notification(
                formatted_message, 
                message_data
            )
            
            logger.info(f"私信处理完成: {message_data['id']}")
            
        except Exception as e:
            ErrorHandler.log_error(e, f"处理私信 {message.get('id', 'unknown')}")
            raise
    
    def _parse_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析私信数据"""
        try:
            # 基本信息
            message_id = message.get('id')
            text = message.get('text', '')
            created_at = message.get('created_at')
            
            if not message_id:
                return None
            
            # 发送者信息
            sender_id = message.get('sender_id')
            
            # 从includes中获取用户信息（如果有的话）
            sender_info = self._extract_user_info(message, sender_id)
            
            # 媒体信息
            media_info = self._extract_media_info(message)
            
            # 时间处理
            timestamp = self._parse_timestamp(created_at)
            
            return {
                'id': message_id,
                'text': text,
                'sender_id': sender_id,
                'sender_info': sender_info,
                'media': media_info,
                'timestamp': timestamp,
                'raw_message': message
            }
            
        except Exception as e:
            logger.error(f"解析私信数据时出错: {e}")
            return None
    
    def _extract_user_info(self, message: Dict[str, Any], sender_id: str) -> Dict[str, Any]:
        """提取发送者用户信息"""
        default_info = {
            'username': f"user_{sender_id}",
            'name': "Unknown User",
            'profile_image_url': None
        }
        
        try:
            # 尝试从includes.users中获取用户信息
            includes = message.get('includes', {})
            users = includes.get('users', [])
            
            for user in users:
                if user.get('id') == sender_id:
                    return {
                        'username': user.get('username', default_info['username']),
                        'name': user.get('name', default_info['name']),
                        'profile_image_url': user.get('profile_image_url')
                    }
            
            # 如果没有找到详细信息，返回默认信息
            return default_info
            
        except Exception as e:
            logger.warning(f"提取用户信息时出错: {e}")
            return default_info
    
    def _extract_media_info(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取媒体信息"""
        media_list = []
        
        try:
            # 检查attachments
            attachments = message.get('attachments', {})
            media_keys = attachments.get('media_keys', [])
            
            if not media_keys:
                return media_list
            
            # 从includes.media中获取媒体详情
            includes = message.get('includes', {})
            media_objects = includes.get('media', [])
            
            for media_key in media_keys:
                for media_obj in media_objects:
                    if media_obj.get('media_key') == media_key:
                        media_info = {
                            'media_key': media_key,
                            'type': media_obj.get('type'),
                            'url': media_obj.get('url'),
                            'preview_image_url': media_obj.get('preview_image_url')
                        }
                        media_list.append(media_info)
                        break
            
        except Exception as e:
            logger.warning(f"提取媒体信息时出错: {e}")
        
        return media_list
    
    def _parse_timestamp(self, created_at: str) -> Optional[datetime]:
        """解析时间戳"""
        if not created_at:
            return None
        
        try:
            # Twitter API返回的是ISO 8601格式
            return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"解析时间戳失败: {e}")
            return None
    
    def _format_message(self, message_data: Dict[str, Any]) -> str:
        """格式化私信为Telegram消息"""
        try:
            sender_info = message_data['sender_info']
            username = sender_info['username']
            name = sender_info['name']
            text = message_data['text'] or "[无文本内容]"
            timestamp = message_data['timestamp']
            message_id = message_data['id']
            
            # 格式化时间
            time_str = "未知时间"
            if timestamp:
                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # 构建消息
            formatted_msg = f"""📩 **Twitter私信通知**

👤 **发送者**: @{username} ({name})
🕒 **时间**: {time_str}
💬 **内容**: {text}

🔗 **消息ID**: {message_id}"""
            
            # 如果有媒体，添加媒体信息
            media = message_data.get('media', [])
            if media:
                media_count = len(media)
                media_types = [m.get('type', 'unknown') for m in media]
                formatted_msg += f"\n📎 **媒体**: {media_count}个文件 ({', '.join(media_types)})"
            
            return formatted_msg
            
        except Exception as e:
            logger.error(f"格式化消息时出错: {e}")
            return f"📩 收到新私信，但格式化失败: {message_data.get('id', 'unknown')}"