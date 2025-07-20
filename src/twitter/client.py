import logging
import tweepy
from typing import Dict, Any, List, Optional
from ..utils.exceptions import TwitterAPIError, RateLimitError
from ..utils.error_handler import handle_errors, ErrorHandler
from ..media.uploader import MediaUploader

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, credentials: Dict[str, str], max_length: int = 280):
        self.max_length = max_length
        self.credentials = credentials
        try:
            self.client = tweepy.Client(
                bearer_token=credentials['bearer_token'],
                consumer_key=credentials['consumer_key'],
                consumer_secret=credentials['consumer_secret'],
                access_token=credentials['access_token'],
                access_token_secret=credentials['access_token_secret'],
                wait_on_rate_limit=True
            )
            # 初始化媒体上传器
            self.media_uploader = MediaUploader(self)
            logger.info("Twitter客户端初始化成功")
        except Exception as e:
            logger.error(f"Twitter客户端初始化失败: {e}")
            raise TwitterAPIError(f"初始化Twitter客户端失败: {e}")
    
    @handle_errors("推文发送失败")
    async def create_tweet(self, text: str) -> Dict[str, Any]:
        """创建推文"""
        try:
            if not self.validate_tweet_length(text):
                raise TwitterAPIError(f"推文长度超过{self.max_length}字符限制")
            
            if not text.strip():
                raise TwitterAPIError("推文内容不能为空")
            
            response = self.client.create_tweet(text=text)
            tweet_id = response.data['id']
            
            logger.info(f"推文创建成功: {tweet_id}")
            return {
                'success': True,
                'tweet_id': tweet_id,
                'text': text,
                'url': f"https://twitter.com/user/status/{tweet_id}"
            }
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"Twitter API频率限制: {e}")
            raise RateLimitError("发送过于频繁，请稍后重试")
        
        except tweepy.Forbidden as e:
            logger.error(f"Twitter API禁止访问: {e}")
            raise TwitterAPIError("没有权限发送推文，请检查API密钥")
        
        except tweepy.Unauthorized as e:
            logger.error(f"Twitter API未授权: {e}")
            raise TwitterAPIError("Twitter API授权失败，请检查凭据")
        
        except tweepy.BadRequest as e:
            logger.error(f"Twitter API请求错误: {e}")
            raise TwitterAPIError(f"推文请求格式错误: {e}")
        
        except Exception as e:
            logger.error(f"Twitter API未知错误: {e}")
            raise TwitterAPIError(f"发送推文时发生错误: {e}")
    
    @handle_errors("带媒体推文发送失败")
    async def create_tweet_with_media(self, text: str, image_paths: List[str]) -> Dict[str, Any]:
        """创建带有图片的推文"""
        try:
            if not self.validate_tweet_length(text):
                raise TwitterAPIError(f"推文长度超过{self.max_length}字符限制")
            
            if len(image_paths) > 4:
                raise TwitterAPIError("最多支持4张图片")
            
            if not image_paths:
                # 如果没有图片，回退到普通推文
                return await self.create_tweet(text)
            
            # 上传媒体文件
            media_ids = self.media_uploader.upload_multiple_media(image_paths)
            
            if not media_ids:
                raise TwitterAPIError("没有成功上传任何图片")
            
            # 创建带媒体的推文
            result = self.media_uploader.create_tweet_with_media(text, media_ids)
            
            logger.info(f"带媒体的推文创建成功: {result['tweet_id']}")
            return result
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"Twitter API频率限制: {e}")
            raise RateLimitError("发送过于频繁，请稍后重试")
        
        except tweepy.Forbidden as e:
            logger.error(f"Twitter API禁止访问: {e}")
            raise TwitterAPIError("没有权限发送推文，请检查API密钥")
        
        except tweepy.Unauthorized as e:
            logger.error(f"Twitter API未授权: {e}")
            raise TwitterAPIError("Twitter API授权失败，请检查凭据")
        
        except tweepy.BadRequest as e:
            logger.error(f"Twitter API请求错误: {e}")
            raise TwitterAPIError(f"推文请求格式错误: {e}")
        
        except Exception as e:
            logger.error(f"Twitter API未知错误: {e}")
            raise TwitterAPIError(f"发送带媒体推文时发生错误: {e}")
    
    def validate_tweet_length(self, text: str) -> bool:
        """验证推文长度"""
        return len(text.strip()) <= self.max_length
    
    def get_tweet_stats(self, text: str) -> Dict[str, int]:
        """获取推文统计信息"""
        return {
            'length': len(text),
            'remaining': self.max_length - len(text),
            'max_length': self.max_length
        }
    
    async def test_connection(self) -> bool:
        """测试Twitter连接"""
        try:
            self.client.get_me()
            logger.info("Twitter连接测试成功")
            return True
        except Exception as e:
            logger.error(f"Twitter连接测试失败: {e}")
            return False
    
    async def get_direct_messages(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """获取私信"""
        try:
            # 使用Twitter API v2获取私信
            response = self.client.get_direct_message_events(
                max_results=max_results,
                dm_event_fields=['id', 'text', 'created_at', 'sender_id', 'attachments'],
                expansions=['sender_id', 'attachments.media_keys'],
                user_fields=['id', 'username', 'name', 'profile_image_url'],
                media_fields=['media_key', 'type', 'url', 'preview_image_url']
            )
            
            if not response.data:
                return []
            
            # 处理响应数据
            messages = []
            for dm_event in response.data:
                message_dict = {
                    'id': dm_event.id,
                    'text': dm_event.text,
                    'created_at': dm_event.created_at.isoformat() if dm_event.created_at else None,
                    'sender_id': dm_event.sender_id,
                }
                
                # 添加附件信息
                if hasattr(dm_event, 'attachments') and dm_event.attachments:
                    message_dict['attachments'] = dm_event.attachments
                
                # 添加includes信息
                if hasattr(response, 'includes'):
                    message_dict['includes'] = {}
                    if response.includes.get('users'):
                        message_dict['includes']['users'] = [
                            {
                                'id': user.id,
                                'username': user.username,
                                'name': user.name,
                                'profile_image_url': getattr(user, 'profile_image_url', None)
                            }
                            for user in response.includes['users']
                        ]
                    if response.includes.get('media'):
                        message_dict['includes']['media'] = [
                            {
                                'media_key': media.media_key,
                                'type': media.type,
                                'url': getattr(media, 'url', None),
                                'preview_image_url': getattr(media, 'preview_image_url', None)
                            }
                            for media in response.includes['media']
                        ]
                
                messages.append(message_dict)
            
            logger.info(f"获取到 {len(messages)} 条私信")
            return messages
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"私信API频率限制: {e}")
            raise RateLimitError("私信API调用过于频繁，请稍后重试")
        
        except tweepy.Forbidden as e:
            logger.error(f"私信API禁止访问: {e}")
            raise TwitterAPIError("没有权限访问私信API，请检查API权限")
        
        except tweepy.Unauthorized as e:
            logger.error(f"私信API未授权: {e}")
            raise TwitterAPIError("私信API授权失败，请检查凭据")
        
        except Exception as e:
            logger.error(f"获取私信时发生错误: {e}")
            raise TwitterAPIError(f"获取私信失败: {e}")
    
    async def test_dm_access(self) -> bool:
        """测试私信API访问权限"""
        try:
            # 尝试获取少量私信来测试权限
            await self.get_direct_messages(max_results=1)
            logger.info("私信API访问测试成功")
            return True
        except TwitterAPIError as e:
            logger.error(f"私信API访问测试失败: {e}")
            return False
        except Exception as e:
            logger.error(f"私信API测试时发生未知错误: {e}")
            return False