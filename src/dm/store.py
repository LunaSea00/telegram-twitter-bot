import json
import logging
import os
from typing import Set, Optional
from datetime import datetime, timedelta
from ..utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)

class DMStore:
    """私信存储管理器 - 负责记录已处理的私信ID，避免重复处理"""
    
    def __init__(self, config):
        self.config = config
        self.store_file = getattr(config, 'dm_store_file', 'data/processed_dm_ids.json')
        self.max_age_days = getattr(config, 'dm_store_max_age_days', 7)
        self.processed_ids: Set[str] = set()
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
        
        # 加载已处理的ID
        self._load_processed_ids()
    
    def is_processed(self, message_id: str) -> bool:
        """检查消息是否已处理"""
        return message_id in self.processed_ids
    
    def mark_processed(self, message_id: str):
        """标记消息为已处理"""
        try:
            self.processed_ids.add(message_id)
            self._save_processed_ids()
            logger.debug(f"标记私信为已处理: {message_id}")
        except Exception as e:
            ErrorHandler.log_error(e, f"标记私信已处理 {message_id}")
    
    def get_processed_count(self) -> int:
        """获取已处理消息数量"""
        return len(self.processed_ids)
    
    def _load_processed_ids(self):
        """从文件加载已处理的ID"""
        try:
            if os.path.exists(self.store_file):
                with open(self.store_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 支持新格式（带时间戳）和旧格式（仅ID列表）
                if isinstance(data, dict):
                    processed_data = data.get('processed_ids', {})
                    cutoff_time = datetime.now() - timedelta(days=self.max_age_days)
                    
                    # 过滤过期的记录
                    for msg_id, timestamp_str in processed_data.items():
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp > cutoff_time:
                                self.processed_ids.add(msg_id)
                        except (ValueError, TypeError):
                            # 如果时间戳格式有问题，保留这个ID
                            self.processed_ids.add(msg_id)
                            
                elif isinstance(data, list):
                    # 旧格式兼容
                    self.processed_ids = set(data)
                
                logger.info(f"加载了 {len(self.processed_ids)} 个已处理私信ID")
            else:
                logger.info("私信存储文件不存在，将创建新文件")
                
        except Exception as e:
            logger.error(f"加载已处理ID失败: {e}")
            self.processed_ids = set()
    
    def _save_processed_ids(self):
        """保存已处理的ID到文件"""
        try:
            # 使用新格式，包含时间戳
            current_time = datetime.now().isoformat()
            processed_data = {
                msg_id: current_time for msg_id in self.processed_ids
            }
            
            data = {
                'version': '1.0',
                'last_updated': current_time,
                'processed_ids': processed_data
            }
            
            # 原子写入
            temp_file = self.store_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 替换原文件
            os.replace(temp_file, self.store_file)
            
            logger.debug(f"保存了 {len(self.processed_ids)} 个已处理私信ID")
            
        except Exception as e:
            ErrorHandler.log_error(e, "保存已处理ID")
    
    def cleanup_old_records(self):
        """清理过期记录"""
        try:
            if not os.path.exists(self.store_file):
                return
            
            original_count = len(self.processed_ids)
            cutoff_time = datetime.now() - timedelta(days=self.max_age_days)
            
            # 重新加载并过滤
            with open(self.store_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'processed_ids' in data:
                processed_data = data['processed_ids']
                new_processed_ids = set()
                
                for msg_id, timestamp_str in processed_data.items():
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp > cutoff_time:
                            new_processed_ids.add(msg_id)
                    except (ValueError, TypeError):
                        # 保留有问题的记录
                        new_processed_ids.add(msg_id)
                
                self.processed_ids = new_processed_ids
                self._save_processed_ids()
                
                cleaned_count = original_count - len(self.processed_ids)
                if cleaned_count > 0:
                    logger.info(f"清理了 {cleaned_count} 个过期私信记录")
            
        except Exception as e:
            ErrorHandler.log_error(e, "清理过期记录")
    
    def get_stats(self) -> dict:
        """获取存储统计信息"""
        return {
            'total_processed': len(self.processed_ids),
            'store_file': self.store_file,
            'max_age_days': self.max_age_days,
            'file_exists': os.path.exists(self.store_file)
        }