import os
from pathlib import Path
from http import HTTPStatus

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from dashscope import ImageSynthesis
    import dashscope
    dashscope.api_key = settings.dashscope_api_key
    USE_MOCK = False
except ImportError:
    from app.services.mock_sdk import MockImageSynthesis as ImageSynthesis
    USE_MOCK = True


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
        # 调用图像生成
        response = ImageSynthesis.call(
            model=self.model,
            prompt=prompt,
            n=1,
            size=size
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"图像生成失败: {response.code} - {response.message}")

        # 获取图片URL并下载
        image_url = response.output.results[0].url

        # 保存图片
        output_path = get_output_path(generation_id, "comic.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 下载图片
        import urllib.request
        urllib.request.urlretrieve(image_url, output_path)

        return output_path


# 单例
image_service = ImageService()
