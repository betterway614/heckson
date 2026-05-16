import json
from typing import Any, Optional
from http import HTTPStatus

from app.config import get_settings
from app.models.model_registry import get_model_registry, ModelTask

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from dashscope import AioGeneration
    import dashscope
    dashscope.api_key = settings.dashscope_api_key
    USE_MOCK = False
except ImportError:
    from app.services.mock_sdk import MockAioGeneration as AioGeneration
    USE_MOCK = True


class LLMService:
    """LLM文案生成服务"""

    def __init__(self):
        self.registry = get_model_registry()

    def _get_model(self, task: ModelTask, model_override: Optional[str] = None) -> str:
        """获取模型名称，支持覆盖"""
        if model_override:
            return model_override
        return self.registry.get_llm_model(task)

    async def generate_script(
        self,
        metadata: dict[str, Any],
        style_prompt: str,
        user_mood: str = "",
        memory_date: str = "",
        model: Optional[str] = None
    ) -> dict[str, str]:
        """
        生成漫画文案

        Args:
            metadata: VLM解析的元数据
            style_prompt: 风格提示词模板
            user_mood: 用户情绪
            memory_date: 记忆日期
            model: 可选的模型覆盖

        Returns:
            dict: {"caption": "...", "scene_description": "...", "bubble_text": "..."}
        """
        # 获取模型
        model_name = self._get_model(ModelTask.SCRIPT_GENERATION, model)

        # 渲染提示词
        prompt = style_prompt.format(
            metadata=json.dumps(metadata, ensure_ascii=False),
            user_mood=user_mood,
            memory_date=memory_date
        )

        # 调用LLM (异步)
        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的漫画文案创作助手，擅长生成有趣的对话和画面描述。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1024,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        # 解析响应
        content = response.output.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "caption": "今日日记",
                "scene_description": content,
                "bubble_text": "..."
            }

    async def polish_prompt(
        self,
        prompt: str,
        style_name: str,
        model: Optional[str] = None
    ) -> str:
        """
        润色用户编辑的提示词

        Args:
            prompt: 用户编辑的提示词
            style_name: 风格名称
            model: 可选的模型覆盖

        Returns:
            str: 润色后的提示词
        """
        # 获取模型
        model_name = self._get_model(ModelTask.PROMPT_POLISH, model)

        system_prompt = f"""你是一个专业的AI绘图提示词润色助手。
用户会给你一段描述场景的文字，你需要将其润色成适合{style_name}风格的AI绘图提示词。

要求：
1. 保持原意不变
2. 增加细节描述，使画面更丰富
3. 添加风格相关的关键词
4. 输出润色后的提示词，不要添加其他解释"""

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=512,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content

    async def analyze_content(
        self,
        content: str,
        analysis_type: str = "general",
        model: Optional[str] = None
    ) -> dict[str, Any]:
        """
        分析内容

        Args:
            content: 要分析的内容
            analysis_type: 分析类型
            model: 可选的模型覆盖

        Returns:
            dict: 分析结果
        """
        model_name = self._get_model(ModelTask.CONTENT_ANALYSIS, model)

        system_prompt = f"""你是一个专业的内容分析助手。
请对用户提供的内容进行{analysis_type}分析，并返回JSON格式的结果。"""

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=0.5,
            max_tokens=1024,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        content = response.output.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_analysis": content}

    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        model: Optional[str] = None
    ) -> str:
        """
        生成摘要

        Args:
            text: 原始文本
            max_length: 最大长度
            model: 可选的模型覆盖

        Returns:
            str: 摘要文本
        """
        model_name = self._get_model(ModelTask.SUMMARY, model)

        system_prompt = f"""你是一个专业的文本摘要助手。
请对用户提供的文本生成简洁的摘要，不超过{max_length}字。"""

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.5,
            max_tokens=512,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content

    async def aggregate_diary(
        self,
        visual_results: list[dict],
        user_text: str,
        model: Optional[str] = None
    ) -> str:
        """
        日记汇总 - 将多图VLM结果 + 用户文本融合为日记正文

        Args:
            visual_results: VLM纯视觉提取结果列表（每张图一个dict）
            user_text: 用户输入的文字
            model: 可选的模型覆盖

        Returns:
            str: 日记正文
        """
        from app.templates.styles import StyleManager

        # 将多图结果整理为可读文本（包含时间信息）
        if visual_results:
            visual_parts = []
            for i, vr in enumerate(visual_results, 1):
                # 提取时间元数据
                meta = vr.get("_meta", {})
                taken_at = meta.get("taken_at")
                time_str = f" (拍摄时间: {taken_at})" if taken_at else ""

                if "raw_text" in vr:
                    visual_parts.append(f"图片{i}{time_str}: {vr['raw_text']}")
                else:
                    parts = []
                    if vr.get("scene"):
                        parts.append(f"场景: {vr['scene']}")
                    if vr.get("objects"):
                        parts.append(f"物品: {', '.join(vr['objects'])}")
                    if vr.get("people"):
                        parts.append(f"人物: {vr['people']}")
                    if vr.get("environment"):
                        parts.append(f"环境: {vr['environment']}")
                    if vr.get("details"):
                        detail_str = vr["details"] if isinstance(vr["details"], str) else ", ".join(vr["details"])
                        parts.append(f"细节: {detail_str}")
                    if vr.get("text_in_image"):
                        parts.append(f"图中文字: {vr['text_in_image']}")
                    visual_parts.append(f"图片{i}{time_str}: {'; '.join(parts)}")
            visual_info = "\n".join(visual_parts)
        else:
            visual_info = ""

        # 获取汇总提示词
        style_manager = StyleManager()
        prompt = style_manager.get_aggregation_prompt(visual_info, user_text)

        model_name = self._get_model(ModelTask.SCRIPT_GENERATION, model)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个情感细腻的日记创作助手，擅长将视觉信息与文字融合成自然流畅的第一人称日记。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=512,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content

    async def polish_diary(
        self,
        diary_text: str,
        style_key: str,
        model: Optional[str] = None
    ) -> str:
        """
        日记润色（支持4种风格：polished/douyin/xiaohongshu/moments）

        Args:
            diary_text: 原始日记文本
            style_key: 润色风格键名
            model: 可选的模型覆盖

        Returns:
            str: 润色后的文本
        """
        from app.templates.styles import StyleManager

        system_prompt = StyleManager.get_polish_prompt(style_key)
        if not system_prompt:
            raise ValueError(f"Unknown polish style: {style_key}")

        model_name = self._get_model(ModelTask.PROMPT_POLISH, model)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": diary_text}
            ],
            temperature=0.8,
            max_tokens=1024,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content

    async def extract_emotion(
        self,
        diary_text: str,
        model: Optional[str] = None
    ) -> dict[str, Any]:
        """
        情绪提取 - 分析日记内容，返回结构化情绪标签

        Args:
            diary_text: 日记文本
            model: 可选的模型覆盖

        Returns:
            dict: {"primary_emotion": "...", "intensity": 0, "bgm_vibe": "...", ...}
        """
        from app.templates.styles import StyleManager

        model_name = self._get_model(ModelTask.CONTENT_ANALYSIS, model)
        prompt_template = StyleManager.get_emotion_prompt()
        system_prompt = prompt_template.format(diary_text=diary_text)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的情绪分析助手，只输出JSON格式的结果。"},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.3,
            max_tokens=512,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        content = response.output.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_emotion": content}

    async def generate_comic_prompt(
        self,
        diary_text: str,
        style_key: str,
        timeline_info: str = "",
        model: Optional[str] = None
    ) -> str:
        """
        漫画分镜提示词生成

        Args:
            diary_text: 润色后的日记文本
            style_key: 漫画风格（comic_shuangwen/comic_zhiyu/comic_timeline）
            timeline_info: 时间线信息（可选，用于 comic_timeline 风格）
            model: 可选的模型覆盖

        Returns:
            str: 生图提示词
        """
        from app.templates.styles import StyleManager

        style_manager = StyleManager()
        prompt = style_manager.get_comic_prompt(style_key, diary_text, timeline_info)

        model_name = self._get_model(ModelTask.SCRIPT_GENERATION, model)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个顶级的AI生图提示词专家，严格按要求输出中文提示词组合。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1024,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content


# 单例
llm_service = LLMService()
