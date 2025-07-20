import logging
import json
from aiohttp import web
from .metrics import metrics_collector

logger = logging.getLogger(__name__)

class HealthServer:
    def __init__(self, port: int = 8000):
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/", self._health_check)
        self.app.router.add_get("/metrics", self._metrics)
        self.app.router.add_get("/status", self._status)
    
    async def _health_check(self, request):
        """健康检查端点"""
        return web.Response(text="OK", status=200)
    
    async def _metrics(self, request):
        """指标端点"""
        try:
            metrics = metrics_collector.get_metrics()
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return web.json_response(
                {"error": "Failed to get metrics"}, 
                status=500
            )
    
    async def _status(self, request):
        """状态端点"""
        try:
            metrics = metrics_collector.get_metrics()
            
            # 确定服务状态
            status = "healthy"
            if metrics['errors']['total'] > 0:
                # 如果错误率过高，标记为不健康
                total_attempts = metrics['tweets_sent'] + metrics_collector.metrics.tweets_failed
                if total_attempts > 0:
                    error_rate = (metrics['errors']['total'] / total_attempts) * 100
                    if error_rate > 50:  # 错误率超过50%
                        status = "unhealthy"
                    elif error_rate > 20:  # 错误率超过20%
                        status = "degraded"
            
            response_data = {
                "status": status,
                "timestamp": metrics.get('last_tweet', 'Never'),
                "uptime": metrics['uptime_human'],
                "metrics": metrics
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return web.json_response(
                {
                    "status": "error",
                    "error": "Failed to get status"
                }, 
                status=500
            )
    
    async def start(self):
        """启动健康检查服务器"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()
            logger.info(f"🌐 健康检查服务器启动在端口 {self.port}")
            logger.info(f"📊 可用端点: /health, /metrics, /status")
        except Exception as e:
            logger.error(f"启动健康检查服务器失败: {e}")
            raise
    
    async def stop(self):
        """停止健康检查服务器"""
        try:
            if self.runner:
                await self.runner.cleanup()
                logger.info("健康检查服务器已停止")
        except Exception as e:
            logger.error(f"停止健康检查服务器失败: {e}")