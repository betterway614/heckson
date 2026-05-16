import base64
from volcenginesdkarkruntime import Ark

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()


class ImageService:
    """图像生成服务"""

    def __init__(self):
        self.client = Ark(api_key=settings.ark_api_key)
        self.model = settings.seedream_endpoint_id

    async def generate_image(
        self,
        prompt: str,
        generation_id: str,
        size: str = "1024x1024"
    ) -> str:
        """
        生成漫画图片

        Args:
            prompt: 生成提示词
            generation_id: 生成任务ID
            size: 图片尺寸

        Returns:
            str: 生成的图片文件路径
        """
        # 调用即梦生成图片
        result = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            response_format="b64_json"
        )

        # 保存图片
        image_data = base64.b64decode(result.data[0].b64_json)
        output_path = get_output_path(generation_id, "comic.png")

        with open(output_path, "wb") as f:
            f.write(image_data)

        return output_path


# 单例
image_service = ImageService()
