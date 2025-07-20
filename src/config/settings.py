import os
import logging
from dotenv import load_dotenv
from typing import Dict, List
from ..utils.exceptions import ConfigurationError

load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    """配置管理类"""
    
    REQUIRED_VARS = {
        'TELEGRAM_BOT_TOKEN': 'Telegram机器人令牌',
        'TWITTER_API_KEY': 'Twitter API密钥',
        'TWITTER_API_SECRET': 'Twitter API密钥',
        'TWITTER_ACCESS_TOKEN': 'Twitter访问令牌',
        'TWITTER_ACCESS_TOKEN_SECRET': 'Twitter访问令牌密钥',
        'TWITTER_BEARER_TOKEN': 'Twitter Bearer令牌',
        'AUTHORIZED_USER_ID': '授权用户ID'
    }
    
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.authorized_user_id = os.getenv('AUTHORIZED_USER_ID')
        
        # 可选配置
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.health_port = int(os.getenv('HEALTH_PORT', '8000'))
        self.tweet_max_length = int(os.getenv('TWEET_MAX_LENGTH', '280'))
        
        # 媒体处理配置
        self.max_image_size = int(os.getenv('MAX_IMAGE_SIZE', '5242880'))  # 5MB
        self.supported_image_formats = os.getenv('SUPPORTED_IMAGE_FORMATS', 'jpg,jpeg,png,gif').split(',')
        self.temp_dir = os.getenv('TEMP_DIR', './temp')
        self.media_upload_timeout = int(os.getenv('MEDIA_UPLOAD_TIMEOUT', '30'))
        
        # DM监听配置
        self.enable_dm_monitoring = os.getenv('ENABLE_DM_MONITORING', 'true').lower() == 'true'
        self.dm_poll_interval = int(os.getenv('DM_POLL_INTERVAL', '60'))
        self.dm_target_chat_id = os.getenv('DM_TARGET_CHAT_ID')
        self.dm_store_file = os.getenv('DM_STORE_FILE', 'data/processed_dm_ids.json')
        self.dm_store_max_age_days = int(os.getenv('DM_STORE_MAX_AGE_DAYS', '7'))
        
        self._validate_config()
        logger.info("配置加载完成")
    
    def _validate_config(self):
        """验证配置参数"""
        missing_vars = []
        
        for var_name, description in self.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value or not value.strip():
                missing_vars.append(f"{var_name} ({description})")
        
        if missing_vars:
            error_msg = f"缺少必需的环境变量:\n" + "\n".join(f"- {var}" for var in missing_vars)
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        # 验证授权用户ID格式
        try:
            int(self.authorized_user_id)
        except ValueError:
            raise ConfigurationError("AUTHORIZED_USER_ID必须是数字")
        
        # 验证端口范围
        if not (1 <= self.health_port <= 65535):
            raise ConfigurationError("HEALTH_PORT必须在1-65535范围内")
        
        # 验证推文长度限制
        if not (1 <= self.tweet_max_length <= 280):
            raise ConfigurationError("TWEET_MAX_LENGTH必须在1-280范围内")
        
        # 验证媒体配置
        if self.max_image_size <= 0:
            raise ConfigurationError("MAX_IMAGE_SIZE必须大于0")
        
        if self.media_upload_timeout <= 0:
            raise ConfigurationError("MEDIA_UPLOAD_TIMEOUT必须大于0")
        
        # 验证DM配置
        if self.enable_dm_monitoring:
            if not self.dm_target_chat_id:
                logger.warning("启用了DM监听但未设置DM_TARGET_CHAT_ID")
            else:
                try:
                    int(self.dm_target_chat_id)
                except ValueError:
                    raise ConfigurationError("DM_TARGET_CHAT_ID必须是数字")
        
        if self.dm_poll_interval <= 0:
            raise ConfigurationError("DM_POLL_INTERVAL必须大于0")
        
        if self.dm_store_max_age_days <= 0:
            raise ConfigurationError("DM_STORE_MAX_AGE_DAYS必须大于0")
    
    @property
    def twitter_credentials(self) -> Dict[str, str]:
        """获取Twitter凭据"""
        return {
            'bearer_token': self.twitter_bearer_token,
            'consumer_key': self.twitter_api_key,
            'consumer_secret': self.twitter_api_secret,
            'access_token': self.twitter_access_token,
            'access_token_secret': self.twitter_access_token_secret
        }
    
    def get_missing_vars(self) -> List[str]:
        """获取缺失的环境变量列表"""
        missing = []
        for var_name in self.REQUIRED_VARS.keys():
            if not os.getenv(var_name):
                missing.append(var_name)
        return missing
    
    def to_dict(self) -> Dict[str, any]:
        """将配置转换为字典（隐藏敏感信息）"""
        return {
            'telegram_token': '***' if self.telegram_token else None,
            'twitter_api_key': '***' if self.twitter_api_key else None,
            'authorized_user_id': self.authorized_user_id,
            'log_level': self.log_level,
            'health_port': self.health_port,
            'tweet_max_length': self.tweet_max_length,
            'max_image_size': self.max_image_size,
            'supported_image_formats': self.supported_image_formats,
            'temp_dir': self.temp_dir,
            'media_upload_timeout': self.media_upload_timeout,
            'enable_dm_monitoring': self.enable_dm_monitoring,
            'dm_poll_interval': self.dm_poll_interval,
            'dm_target_chat_id': '***' if self.dm_target_chat_id else None,
            'dm_store_file': self.dm_store_file,
            'dm_store_max_age_days': self.dm_store_max_age_days
        }

# 全局配置实例
config = None

def get_config() -> Config:
    """获取配置实例（单例模式）"""
    global config
    if config is None:
        config = Config()
    return config