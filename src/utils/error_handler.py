import logging
from typing import Optional, Callable, Any
from functools import wraps
from .exceptions import *

logger = logging.getLogger(__name__)

def handle_errors(fallback_message: str = "操作失败，请稍后重试"):
    """装饰器：处理函数中的异常"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except TwitterAPIError as e:
                logger.error(f"Twitter API错误: {e}")
                return {"success": False, "error": f"Twitter API错误: {e}"}
            except TelegramAPIError as e:
                logger.error(f"Telegram API错误: {e}")
                return {"success": False, "error": f"Telegram错误: {e}"}
            except AuthorizationError as e:
                logger.warning(f"授权错误: {e}")
                return {"success": False, "error": "权限不足"}
            except Exception as e:
                logger.error(f"未预期的错误: {e}")
                return {"success": False, "error": fallback_message}
        
        return wrapper
    return decorator

class ErrorHandler:
    """统一错误处理器"""
    
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """记录错误日志"""
        if context:
            logger.error(f"[{context}] {type(error).__name__}: {error}")
        else:
            logger.error(f"{type(error).__name__}: {error}")
    
    @staticmethod
    def format_user_error(error: Exception) -> str:
        """格式化用户友好的错误信息"""
        if isinstance(error, TwitterAPIError):
            return f"Twitter服务错误: {error}"
        elif isinstance(error, AuthorizationError):
            return "❌ 你没有权限执行此操作"
        elif isinstance(error, RateLimitError):
            return "⏰ 请求过于频繁，请稍后重试"
        elif isinstance(error, ConfigurationError):
            return "配置错误，请联系管理员"
        else:
            return "❌ 操作失败，请稍后重试"