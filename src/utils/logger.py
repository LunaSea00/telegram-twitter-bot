import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None, max_bytes: int = 10*1024*1024, backup_count: int = 5):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
    """
    # 创建日志目录
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，级别: {log_level}")
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """获取日志器"""
    return logging.getLogger(name or __name__)