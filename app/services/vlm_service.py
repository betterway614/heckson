import json
import base64
from typing import Any, Optional
from http import HTTPStatus

from dashscope import MultiModalConversation
import dashscope

from app.config import get_settings

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


class VLMService:
    """VLM视觉解析服务 - 统一识别图片信息"""

    def __init__(self):
        self.model = settings.vlm_model

    async def parse_image(
        self,
        image_path: str,
        prompt: str,
        user_text: str = "",
        model: Optional[str] = None
    ) -> dict[str, Any]:
        """
        解析图片，提取场景、情绪、物品等信息

        Args:
            image_path: 图片文件路径
            prompt: 解析提示词
            user_text: 用户附加文字（用于日记替身融合）
            model: 可选的模型覆盖

        Returns:
            dict: 解析结果
        """
        # 使用指定模型或默认模型
        model_name = model or self.model

        # 如果有用户文字，将其融入提示词
        if user_text:
            prompt = prompt.replace("{user_text}", user_text)

        # 调用VLM多模态模型
        response = MultiModalConversation.call(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"image": f"file://{image_path}"},
                        {"text": prompt}
                    ]
                }
            ]
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"VLM调用失败: {response.code} - {response.message}")

        # 解析响应
        content = response.output.choices[0].message.content[0]["text"]
        try:
            # 处理VLM返回的markdown代码块包裹的JSON
            cleaned = content.strip()
            if cleaned.startswith("```"):
                # 移除首尾的代码块标记
                lines = cleaned.split("\n")
                # 移除第一行（```json 或 ```）
                lines = lines[1:]
                # 移除最后一行（```）
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw_text": content}


# 单例
vlm_service = VLMService()
