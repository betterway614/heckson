import json
from typing import Any, Optional
from http import HTTPStatus

from dashscope import AioGeneration
import dashscope

from app.config import get_settings
from app.models.model_registry import get_model_registry, ModelTask

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


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

    async def polish_text(
        self,
        text: str,
        style_key: str,
        model: Optional[str] = None
    ) -> str:
        """
        独立文本润色（不依赖generation）

        Args:
            text: 原始文本
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
                {"role": "user", "content": text}
            ],
            temperature=0.8,
            max_tokens=1024,
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

    async def generate_daily_diary_prompt(
        self,
        memory_date: str,
        all_memories: list[dict],
        model: Optional[str] = None
    ) -> str:
        """
        一日漫画汇总 - 将当天所有记忆按时间顺序汇总为漫画提示词

        Args:
            memory_date: 日期字符串 (如 "2026年05月17日")
            all_memories: 当天所有记忆列表，每项包含:
                - time: 时间字符串
                - text: 用户文字
                - visual_info: VLM视觉提取结果
            model: 可选的模型覆盖

        Returns:
            str: 漫画生图提示词
        """
        from app.templates.styles import StyleManager

        # 将所有记忆整理为可读文本
        memory_parts = []
        for i, mem in enumerate(all_memories, 1):
            time_str = mem.get("time", "未知时间")
            text = mem.get("text", "")
            visual = mem.get("visual_info", "")

            part = f"【记忆{i} - {time_str}】"
            if text:
                part += f"\n  文字记录：{text}"
            if visual:
                part += f"\n  画面描述：{visual}"
            memory_parts.append(part)

        all_memories_str = "\n\n".join(memory_parts)

        # 获取提示词
        prompt = StyleManager.get_daily_diary_prompt(memory_date, all_memories_str)

        model_name = self._get_model(ModelTask.SCRIPT_GENERATION, model)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个顶级的漫画分镜导演和AI生图提示词专家，严格按要求输出中文提示词组合。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1024,
            result_format='message'
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"LLM调用失败: {response.code} - {response.message}")

        return response.output.choices[0].message.content

    async def polish_diary_with_visual(
        self,
        user_text: str,
        visual_text: str,
        model: Optional[str] = None
    ) -> str:
        """
        结合图片内容和用户文字润色日记

        Args:
            user_text: 用户输入的文字
            visual_text: VLM解析的视觉描述
            model: 可选的模型覆盖

        Returns:
            str: 润色后的日记文本
        """
        model_name = self._get_model(ModelTask.PROMPT_POLISH, model)

        system_prompt = """你是一个情感细腻、极具生活洞察力的"日记替身"。你的任务是将[用户文字]与[画面描述]融合，代写一段第一人称日记。

# 融合策略
1. 以文为骨：将用户的文字作为日记的核心事件和真实情绪基调。绝对不要反驳或偏离用户的文字原意。
2. 以图为肉：从画面描述中提取细节（如场景、物品、环境氛围），用来扩写和丰富文字中的场景感。
3. 补全脑补：如果用户的文字非常简短（如"烦死了"），请根据画面描述合理脑补出"为什么烦"。
4. 如果用户未输入文字，则以画面描述为主，创作一段自然的场景日记。

# 画面描述格式说明
画面描述由AI从图片中提取，格式为"场景: xxx; 物品: xxx; 人物: xxx; 环境: xxx; 细节: xxx"，请将其理解为图片中的视觉信息。

# Output Rules (严格遵守)
1. 视角与语气：必须使用第一人称（"我"）。口语化、自然，像是极具个性的朋友圈或手账文案。
2. 禁忌词汇：绝对禁止出现"用户说"、"图片展示了"、"结合图片和文字来看"、"可以看出"、"画面描述中"等生硬的机器分析句式。
3. 长度约束：字数严格控制在 50 - 120 字之间，紧凑有张力。
4. 不要添加emoji或特殊符号。
5. 纯净输出：直接输出日记正文，不要有任何前缀、标题或解释。"""

        prompt = f"""用户文字：
{user_text if user_text else "（用户未输入文字）"}

画面描述：
{visual_text if visual_text else "（无图片或图片解析失败）"}"""

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

    async def generate_video_script(
        self,
        memories: list,
        style: str = "cinematic"
    ) -> str:
        """
        根据记忆生成视频脚本

        Args:
            memories: 记忆列表（已按日期排序）
            style: 视频风格

        Returns:
            str: 视频脚本
        """
        # 构建记忆文本
        memory_texts = []
        for i, memory in enumerate(memories, 1):
            date_str = memory.memory_date.strftime("%Y年%m月%d日")
            text = memory.content_text or "图片记忆"
            memory_texts.append(f"{i}. [{date_str}] {text}")

        memories_str = "\n".join(memory_texts)

        prompt = f"""你是一位专业的视频脚本编剧。请根据以下记忆内容，创作一个 15 秒的视频脚本。

记忆内容（按时间顺序）：
{memories_str}

视频风格：{style}

要求：
1. 脚本应以时间顺序串联这些记忆
2. 语言生动、有画面感
3. 适合 15 秒视频的节奏
4. 包含场景描述和旁白文字

请直接输出脚本内容，不要包含其他说明。"""

        model_name = self._get_model(ModelTask.SCRIPT_GENERATION)

        response = await AioGeneration.call(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的视频脚本编剧，擅长创作富有感染力的短视频脚本。"},
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
