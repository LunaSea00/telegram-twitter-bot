import logging
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Any, List
from ..utils.exceptions import AuthorizationError, TwitterAPIError
from ..utils.error_handler import ErrorHandler
from ..media.processor import MediaProcessor

logger = logging.getLogger(__name__)

class TelegramHandlers:
    def __init__(self, twitter_client, auth_service, config):
        self.twitter_client = twitter_client
        self.auth_service = auth_service
        self.config = config
        self.media_processor = MediaProcessor(config)
    
    def _check_authorization(self, user_id: int) -> bool:
        """检查用户授权"""
        if not self.auth_service.is_authorized(user_id):
            raise AuthorizationError(f"用户 {user_id} 未授权")
        return True
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self._check_authorization(update.effective_user.id)
            
            welcome_msg = (
                f"🎉 欢迎使用 Twitter Bot！\n\n"
                f"👤 授权用户: {update.effective_user.first_name}\n"
                f"📝 直接发送消息即可发布到Twitter\n"
                f"📏 消息长度限制: {self.config.tweet_max_length}字符\n\n"
                f"使用 /help 查看更多命令"
            )
            await update.message.reply_text(welcome_msg)
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "start命令")
            await update.message.reply_text("❌ 服务暂时不可用，请稍后重试。")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self._check_authorization(update.effective_user.id)
            
            help_text = f"""
📖 **使用帮助**

**基本命令：**
• `/start` - 开始使用机器人
• `/help` - 显示此帮助信息
• `/status` - 检查服务状态
• `/stats <消息>` - 查看消息统计信息

**发送推文：**
• 直接发送文本消息即可发布到Twitter
• 消息长度限制：{self.config.tweet_max_length}字符
• 支持中英文混合内容

**发送图片推文：**
• 发送图片（支持最多4张）
• 支持格式：JPG, PNG, GIF
• 文件大小限制：{self.config.max_image_size // 1024 // 1024}MB
• 可以添加图片说明文字

**DM监听功能：**
• `/dm_status` - 查看私信监听状态
• 自动监听Twitter私信并转发到此聊天
• 监听间隔：{getattr(self.config, 'dm_poll_interval', 60)}秒

**注意事项：**
• 只有授权用户可以使用此机器人
• 请遵守Twitter使用条款
• 发送前请仔细检查内容
• 支持私信和群聊消息

🔗 发送成功后会返回推文链接
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "help命令")
            await update.message.reply_text("❌ 无法显示帮助信息。")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """检查服务状态"""
        try:
            self._check_authorization(update.effective_user.id)
            
            # 测试Twitter连接
            twitter_status = await self.twitter_client.test_connection()
            
            status_msg = (
                f"🔧 **服务状态**\n\n"
                f"Twitter API: {'✅ 正常' if twitter_status else '❌ 异常'}\n"
                f"机器人状态: ✅ 运行中\n"
                f"配置状态: ✅ 已加载\n"
                f"推文长度限制: {self.config.tweet_max_length}字符"
            )
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "status命令")
            await update.message.reply_text("❌ 无法获取状态信息。")
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示消息统计信息"""
        try:
            self._check_authorization(update.effective_user.id)
            
            if not context.args:
                await update.message.reply_text("使用方法: /stats <消息内容>")
                return
            
            text = ' '.join(context.args)
            stats = self.twitter_client.get_tweet_stats(text)
            
            stats_msg = (
                f"📊 **消息统计**\n\n"
                f"📝 内容: {text[:50]}{'...' if len(text) > 50 else ''}\n"
                f"📏 长度: {stats['length']} 字符\n"
                f"📋 剩余: {stats['remaining']} 字符\n"
                f"🚦 状态: {'✅ 可发送' if stats['remaining'] >= 0 else '❌ 超出限制'}"
            )
            await update.message.reply_text(stats_msg, parse_mode='Markdown')
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "stats命令")
            await update.message.reply_text("❌ 无法获取统计信息。")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            self._check_authorization(update.effective_user.id)
            
            message_text = update.message.text.strip()
            
            if not message_text:
                await update.message.reply_text("❌ 消息内容不能为空。")
                return
            
            # 显示处理状态
            status_msg = await update.message.reply_text("⏳ 正在发送推文...")
            
            # 发送推文
            result = await self.twitter_client.create_tweet(message_text)
            
            if result['success']:
                success_msg = (
                    f"✅ **推文发送成功！**\n\n"
                    f"🆔 推文ID: `{result['tweet_id']}`\n"
                    f"📝 内容: {result['text']}\n"
                    f"🔗 链接: {result['url']}"
                )
                await status_msg.edit_text(success_msg, parse_mode='Markdown')
            else:
                error_msg = ErrorHandler.format_user_error(Exception(result.get('error', '未知错误')))
                await status_msg.edit_text(error_msg)
                
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "消息处理")
            error_msg = ErrorHandler.format_user_error(e)
            await update.message.reply_text(error_msg)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理图片消息"""
        try:
            self._check_authorization(update.effective_user.id)
            
            # 获取消息中的图片
            photos = update.message.photo
            if not photos:
                await update.message.reply_text("❌ 没有找到图片。")
                return
            
            # 获取最大尺寸的图片
            largest_photo = max(photos, key=lambda x: x.file_size)
            
            # 获取标题文本
            caption = update.message.caption or ""
            
            await self._process_media_message(
                update, 
                [largest_photo.file_id], 
                caption, 
                "图片"
            )
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "图片处理")
            error_msg = ErrorHandler.format_user_error(e)
            await update.message.reply_text(error_msg)
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文档消息（包括图片文件）"""
        try:
            self._check_authorization(update.effective_user.id)
            
            document = update.message.document
            if not document:
                await update.message.reply_text("❌ 没有找到文档。")
                return
            
            # 检查是否为图片文件
            if not document.mime_type or not document.mime_type.startswith('image/'):
                await update.message.reply_text("❌ 只支持图片文件。")
                return
            
            # 检查文件大小
            max_size = getattr(self.config, 'max_image_size', 5242880)  # 5MB
            if document.file_size and document.file_size > max_size:
                await update.message.reply_text(f"❌ 文件大小超过限制（{max_size // 1024 // 1024}MB）。")
                return
            
            # 获取标题文本
            caption = update.message.caption or ""
            
            await self._process_media_message(
                update, 
                [document.file_id], 
                caption, 
                "文档"
            )
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "文档处理")
            error_msg = ErrorHandler.format_user_error(e)
            await update.message.reply_text(error_msg)
    
    async def _process_media_message(self, update: Update, file_ids: List[str], text: str, media_type: str):
        """处理媒体消息的通用方法"""
        try:
            # 显示处理状态
            status_msg = await update.message.reply_text(f"⏳ 正在处理{media_type}并发送推文...")
            
            # 获取文件URL
            file_urls = []
            for file_id in file_ids:
                try:
                    file = await update.message.bot.get_file(file_id)
                    file_urls.append(file.file_path)
                except Exception as e:
                    logger.error(f"获取文件URL失败: {e}")
                    continue
            
            if not file_urls:
                await status_msg.edit_text("❌ 无法获取文件，请重试。")
                return
            
            # 处理图片
            processed_images = await self.media_processor.process_images(file_urls)
            
            if not processed_images:
                await status_msg.edit_text("❌ 没有可用的图片文件。")
                return
            
            try:
                # 获取图片文件路径
                image_paths = [img['temp_path'] for img in processed_images]
                
                # 发送带媒体的推文
                result = await self.twitter_client.create_tweet_with_media(text, image_paths)
                
                if result['success']:
                    success_msg = (
                        f"✅ **推文发送成功！**\n\n"
                        f"🆔 推文ID: `{result['tweet_id']}`\n"
                        f"📝 内容: {result['text']}\n"
                        f"🖼️ 图片数量: {result.get('media_count', len(image_paths))}\n"
                        f"🔗 链接: {result['url']}"
                    )
                    await status_msg.edit_text(success_msg, parse_mode='Markdown')
                else:
                    error_msg = ErrorHandler.format_user_error(Exception(result.get('error', '未知错误')))
                    await status_msg.edit_text(error_msg)
                    
            finally:
                # 清理临时文件
                self.media_processor.cleanup_processed_images(processed_images)
                
        except Exception as e:
            ErrorHandler.log_error(e, f"{media_type}消息处理")
            error_msg = ErrorHandler.format_user_error(e)
            await update.message.reply_text(error_msg)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """全局错误处理器"""
        logger.error(f"Telegram错误: {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ 处理消息时发生错误，请稍后重试。"
            )
    
    async def dm_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示DM监听状态"""
        try:
            self._check_authorization(update.effective_user.id)
            
            # 这里需要从主程序获取DM监听器状态
            # 暂时显示配置信息
            dm_enabled = getattr(self.config, 'enable_dm_monitoring', False)
            dm_interval = getattr(self.config, 'dm_poll_interval', 60)
            dm_target = getattr(self.config, 'dm_target_chat_id', None)
            
            status_msg = f"""🔍 **DM监听状态**

⚙️ **功能状态**: {'✅ 启用' if dm_enabled else '❌ 禁用'}
⏱️ **轮询间隔**: {dm_interval}秒
📱 **目标聊天**: {dm_target if dm_target else '未设置'}

💡 **说明**: 
DM监听功能会定期检查您的Twitter私信，并将新消息转发到指定的Telegram聊天中。
"""
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except AuthorizationError:
            await update.message.reply_text("❌ 你没有权限使用此机器人。")
        except Exception as e:
            ErrorHandler.log_error(e, "dm_status命令")
            await update.message.reply_text("❌ 无法获取DM状态信息。")