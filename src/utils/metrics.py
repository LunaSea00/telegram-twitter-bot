import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class Metrics:
    """应用指标"""
    start_time: float = field(default_factory=time.time)
    tweets_sent: int = 0
    tweets_failed: int = 0
    messages_received: int = 0
    errors_total: int = 0
    last_tweet_time: Optional[float] = None
    last_error_time: Optional[float] = None
    
    # 错误统计
    twitter_api_errors: int = 0
    telegram_api_errors: int = 0
    auth_failures: int = 0
    
    def __post_init__(self):
        self._lock = Lock()
    
    def increment_tweets_sent(self):
        """增加发送推文计数"""
        with self._lock:
            self.tweets_sent += 1
            self.last_tweet_time = time.time()
    
    def increment_tweets_failed(self):
        """增加失败推文计数"""
        with self._lock:
            self.tweets_failed += 1
    
    def increment_messages_received(self):
        """增加接收消息计数"""
        with self._lock:
            self.messages_received += 1
    
    def increment_errors(self, error_type: str = "general"):
        """增加错误计数"""
        with self._lock:
            self.errors_total += 1
            self.last_error_time = time.time()
            
            if error_type == "twitter_api":
                self.twitter_api_errors += 1
            elif error_type == "telegram_api":
                self.telegram_api_errors += 1
            elif error_type == "auth":
                self.auth_failures += 1
    
    def get_uptime(self) -> float:
        """获取运行时间（秒）"""
        return time.time() - self.start_time
    
    def get_success_rate(self) -> float:
        """获取推文成功率"""
        total = self.tweets_sent + self.tweets_failed
        if total == 0:
            return 0.0
        return (self.tweets_sent / total) * 100
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        uptime = self.get_uptime()
        return {
            'uptime_seconds': uptime,
            'uptime_human': self._format_uptime(uptime),
            'tweets_sent': self.tweets_sent,
            'tweets_failed': self.tweets_failed,
            'messages_received': self.messages_received,
            'success_rate': f"{self.get_success_rate():.1f}%",
            'errors': {
                'total': self.errors_total,
                'twitter_api': self.twitter_api_errors,
                'telegram_api': self.telegram_api_errors,
                'auth_failures': self.auth_failures
            },
            'last_tweet': self._format_time(self.last_tweet_time),
            'last_error': self._format_time(self.last_error_time)
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}天{hours}小时{minutes}分钟"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"
    
    def _format_time(self, timestamp: Optional[float]) -> str:
        """格式化时间戳"""
        if timestamp is None:
            return "从未"
        
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = Metrics()
        self._lock = Lock()
    
    def record_tweet_sent(self):
        """记录推文发送"""
        self.metrics.increment_tweets_sent()
        logger.debug("推文发送计数+1")
    
    def record_tweet_failed(self):
        """记录推文失败"""
        self.metrics.increment_tweets_failed()
        logger.debug("推文失败计数+1")
    
    def record_message_received(self):
        """记录消息接收"""
        self.metrics.increment_messages_received()
        logger.debug("消息接收计数+1")
    
    def record_error(self, error_type: str = "general"):
        """记录错误"""
        self.metrics.increment_errors(error_type)
        logger.debug(f"错误计数+1: {error_type}")
    
    def get_metrics(self) -> Dict:
        """获取所有指标"""
        return self.metrics.to_dict()
    
    def log_metrics(self):
        """输出指标到日志"""
        metrics = self.get_metrics()
        logger.info(f"📊 应用指标 - 运行时间: {metrics['uptime_human']}, "
                   f"推文: {metrics['tweets_sent']}/{metrics['tweets_sent'] + self.metrics.tweets_failed}, "
                   f"成功率: {metrics['success_rate']}, 错误: {metrics['errors']['total']}")

# 全局指标收集器实例
metrics_collector = MetricsCollector()