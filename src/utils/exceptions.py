class BotException(Exception):
    """Bot基础异常类"""
    pass

class ConfigurationError(BotException):
    """配置错误异常"""
    pass

class TwitterAPIError(BotException):
    """Twitter API错误异常"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

class TelegramAPIError(BotException):
    """Telegram API错误异常"""
    pass

class AuthorizationError(BotException):
    """授权错误异常"""
    pass

class RateLimitError(TwitterAPIError):
    """频率限制错误异常"""
    pass