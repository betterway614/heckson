import json
import base64
from typing import Any
from volcenginesdkarkruntime import Ark

from app.config import get_settings

settings = get_settings()


class VLMService:
    """VLM视觉解析服务"""

    def __init__(self):
        self.client = Ark(api_key=settings.ark_api_key)
        self.model = settings.doubao_vlm_endpoint_id

    async def parse_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        """
        解析图片，提取场景、情绪、物品等信息

        Args:
            image_path: 图片文件路径
            prompt: 解析提示词

        Returns:
            dict: 解析结果
        """
        # 读取图片并转base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # 调用VLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=1024
        )

        # 解析响应
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_text": content}


# 单例
vlm_service = VLMService()
