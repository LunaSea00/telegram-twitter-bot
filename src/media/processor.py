import os
import logging
import tempfile
import aiohttp
from typing import List, Dict, Any, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self, config):
        self.config = config
        self.max_image_size = getattr(config, 'max_image_size', 5242880)  # 5MB
        self.supported_formats = getattr(config, 'supported_image_formats', ['jpg', 'jpeg', 'png', 'gif'])
        self.temp_dir = getattr(config, 'temp_dir', './temp')
        self.media_timeout = getattr(config, 'media_upload_timeout', 30)
        
        # 创建临时目录
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def download_file(self, file_url: str, session: aiohttp.ClientSession) -> Optional[bytes]:
        """下载文件并返回字节数据"""
        try:
            async with session.get(file_url, timeout=aiohttp.ClientTimeout(total=self.media_timeout)) as response:
                if response.status == 200:
                    file_data = await response.read()
                    
                    if len(file_data) > self.max_image_size:
                        logger.warning(f"文件大小超过限制: {len(file_data)} bytes")
                        return None
                    
                    return file_data
                else:
                    logger.error(f"下载文件失败，状态码: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"下载文件时出错: {e}")
            return None
    
    def validate_image_format(self, file_data: bytes) -> bool:
        """验证图片格式"""
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                format_lower = img.format.lower() if img.format else 'unknown'
                return format_lower in self.supported_formats
        except Exception as e:
            logger.error(f"验证图片格式时出错: {e}")
            return False
    
    def optimize_image(self, file_data: bytes, max_size: int = None) -> bytes:
        """优化图片大小和质量"""
        try:
            max_size = max_size or self.max_image_size
            
            with Image.open(io.BytesIO(file_data)) as img:
                # 转换为RGB（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 如果文件已经足够小，直接返回
                if len(file_data) <= max_size:
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85, optimize=True)
                    return output.getvalue()
                
                # 计算缩放比例
                quality = 85
                while True:
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= max_size or quality <= 30:
                        return compressed_data
                    
                    quality -= 10
                
        except Exception as e:
            logger.error(f"优化图片时出错: {e}")
            return file_data
    
    def save_temp_file(self, file_data: bytes, extension: str = 'jpg') -> str:
        """保存临时文件并返回文件路径"""
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.temp_dir, 
                suffix=f'.{extension}', 
                delete=False
            ) as temp_file:
                temp_file.write(file_data)
                return temp_file.name
        except Exception as e:
            logger.error(f"保存临时文件时出错: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"清理临时文件: {file_path}")
        except Exception as e:
            logger.error(f"清理临时文件时出错: {e}")
    
    async def process_images(self, file_urls: List[str]) -> List[Dict[str, Any]]:
        """处理多个图片文件"""
        if len(file_urls) > 4:
            raise ValueError("最多支持4张图片")
        
        processed_images = []
        
        async with aiohttp.ClientSession() as session:
            for i, file_url in enumerate(file_urls):
                try:
                    # 下载文件
                    file_data = await self.download_file(file_url, session)
                    if not file_data:
                        logger.warning(f"跳过无法下载的文件: {file_url}")
                        continue
                    
                    # 验证格式
                    if not self.validate_image_format(file_data):
                        logger.warning(f"跳过不支持的图片格式: {file_url}")
                        continue
                    
                    # 优化图片
                    optimized_data = self.optimize_image(file_data)
                    
                    # 保存临时文件
                    temp_path = self.save_temp_file(optimized_data, 'jpg')
                    
                    processed_images.append({
                        'index': i,
                        'temp_path': temp_path,
                        'size': len(optimized_data),
                        'original_url': file_url
                    })
                    
                    logger.info(f"成功处理图片 {i+1}/{len(file_urls)}: {temp_path}")
                    
                except Exception as e:
                    logger.error(f"处理图片时出错: {e}")
                    continue
        
        return processed_images
    
    def cleanup_processed_images(self, processed_images: List[Dict[str, Any]]):
        """清理所有处理过的图片文件"""
        for image_info in processed_images:
            self.cleanup_temp_file(image_info['temp_path'])