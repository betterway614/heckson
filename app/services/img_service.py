import os
from pathlib import Path
from http import HTTPStatus

from dashscope import ImageSynthesis
import dashscope

from app.config import get_settings
from app.utils.file_utils import get_output_path, get_output_filesystem_path

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


class ImageService:
    """图像生成服务"""

    def __init__(self):
        self.model = settings.image_model

    async def generate_image(
        self,
        prompt: str,
        generation_id: str,
        size: str = "1024*1024"
    ) -> str:
        """
        生成图片（风格由提示词模板决定）

        Args:
            prompt: 生成提示词（已包含风格信息）
            generation_id: 生成任务ID
            size: 图片尺寸

        Returns:
            str: 生成的图片文件路径
        """
        import asyncio

        # 调用图像生成（使用同步调用，在线程池中执行避免阻塞）
        response = await asyncio.to_thread(
            ImageSynthesis.call,
            model=self.model,
            prompt=prompt,
            n=1,
            size=size
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"图像生成失败: {response.code} - {response.message}")

        # 获取图片URL并下载
        image_url = response.output.results[0].url

        # 保存图片 - 使用文件系统路径写入，返回相对路径用于数据库存储
        fs_path = get_output_filesystem_path(generation_id, "comic.png")
        Path(fs_path).parent.mkdir(parents=True, exist_ok=True)

        # 下载图片（使用线程池避免阻塞）
        await asyncio.to_thread(
            __import__('urllib.request', fromlist=['urlretrieve']).urlretrieve,
            image_url,
            fs_path
        )

        # 返回 URL 友好的相对路径
        return get_output_path(generation_id, "comic.png")


# 单例
image_service = ImageService()
