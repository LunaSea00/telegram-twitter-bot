import logging
import tweepy
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class MediaUploader:
    def __init__(self, twitter_client):
        self.client = twitter_client.client  # tweepy.Client
        # 初始化API v1.1客户端用于媒体上传
        auth = tweepy.OAuth1UserHandler(
            consumer_key=twitter_client.credentials['consumer_key'],
            consumer_secret=twitter_client.credentials['consumer_secret'],
            access_token=twitter_client.credentials['access_token'],
            access_token_secret=twitter_client.credentials['access_token_secret']
        )
        self.api = tweepy.API(auth)
    
    def upload_media(self, file_path: str) -> Optional[str]:
        """上传单个媒体文件并返回media_id"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 使用Twitter API v1.1上传媒体
            media = self.api.media_upload(file_path)
            logger.info(f"媒体上传成功: {media.media_id}")
            return str(media.media_id)
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"媒体上传频率限制: {e}")
            raise
        except tweepy.Forbidden as e:
            logger.error(f"媒体上传被禁止: {e}")
            raise
        except tweepy.BadRequest as e:
            logger.error(f"媒体上传请求错误: {e}")
            raise
        except Exception as e:
            logger.error(f"媒体上传失败: {e}")
            return None
    
    def upload_multiple_media(self, file_paths: List[str]) -> List[str]:
        """上传多个媒体文件并返回media_ids列表"""
        if len(file_paths) > 4:
            raise ValueError("最多支持4个媒体文件")
        
        media_ids = []
        uploaded_files = []
        
        try:
            for file_path in file_paths:
                media_id = self.upload_media(file_path)
                if media_id:
                    media_ids.append(media_id)
                    uploaded_files.append(file_path)
                    logger.info(f"成功上传媒体: {file_path} -> {media_id}")
                else:
                    logger.warning(f"跳过上传失败的文件: {file_path}")
            
            if not media_ids:
                raise Exception("没有成功上传任何媒体文件")
            
            logger.info(f"成功上传 {len(media_ids)} 个媒体文件")
            return media_ids
            
        except Exception as e:
            logger.error(f"批量上传媒体时出错: {e}")
            # 清理已上传的媒体（如果API支持的话）
            raise
    
    def create_tweet_with_media(self, text: str, media_ids: List[str]) -> Dict[str, Any]:
        """创建带有媒体的推文"""
        try:
            if len(media_ids) > 4:
                raise ValueError("最多支持4个媒体文件")
            
            # 使用Twitter API v2创建带媒体的推文
            response = self.client.create_tweet(
                text=text,
                media_ids=media_ids
            )
            
            tweet_id = response.data['id']
            logger.info(f"带媒体的推文创建成功: {tweet_id}")
            
            return {
                'success': True,
                'tweet_id': tweet_id,
                'text': text,
                'media_count': len(media_ids),
                'url': f"https://twitter.com/user/status/{tweet_id}"
            }
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"推文创建频率限制: {e}")
            raise
        except tweepy.Forbidden as e:
            logger.error(f"推文创建被禁止: {e}")
            raise
        except tweepy.BadRequest as e:
            logger.error(f"推文创建请求错误: {e}")
            raise
        except Exception as e:
            logger.error(f"创建带媒体的推文失败: {e}")
            raise