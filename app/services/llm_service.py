import json
from typing import Any
from volcenginesdkarkruntime import Ark

from app.config import get_settings

settings = get_settings()


class LLMService:
    """LLM文案生成服务"""

    def __init__(self):
        self.client = Ark(api_key=settings.ark_api_key)
        self.model = settings.doubao_endpoint_id

    async def generate_script(
        self,
        metadata: dict[str, Any],
        style_prompt: str,
        user_mood: str = "",
        memory_date: str = ""
    ) -> dict[str, str]:
        """
        生成漫画文案

        Args:
            metadata: VLM解析的元数据
            style_prompt: 风格提示词模板
            user_mood: 用户情绪
            memory_date: 记忆日期

        Returns:
            dict: {"caption": "...", "scene_description": "...", "bubble_text": "..."}
        """
        # 渲染提示词
        prompt = style_prompt.format(
            metadata=json.dumps(metadata, ensure_ascii=False),
            user_mood=user_mood,
            memory_date=memory_date
        )

        # 调用LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的漫画文案创作助手，擅长生成有趣的对话和画面描述。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1024
        )

        # 解析响应
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "caption": "今日日记",
                "scene_description": content,
                "bubble_text": "..."
            }

    async def polish_prompt(self, prompt: str, style_name: str) -> str:
        """
        润色用户编辑的提示词

        Args:
            prompt: 用户编辑的提示词
            style_name: 风格名称

        Returns:
            str: 润色后的提示词
        """
        system_prompt = f"""你是一个专业的AI绘图提示词润色助手。
用户会给你一段描述场景的文字，你需要将其润色成适合{style_name}风格的AI绘图提示词。

要求：
1. 保持原意不变
2. 增加细节描述，使画面更丰富
3. 添加风格相关的关键词
4. 输出润色后的提示词，不要添加其他解释"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=512
        )

        return response.choices[0].message.content


# 单例
llm_service = LLMService()
