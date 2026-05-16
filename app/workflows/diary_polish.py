import os
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.generation import Generation
from app.models.memory import Memory
from app.models.media import Media
from app.workflows.base import BaseWorkflow
from app.services.vlm_service import vlm_service
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager
from app.config import get_settings


class DiaryPolishWorkflow(BaseWorkflow):
    """
    日记润色工作流（新流程）

    用户上传图片+文字后，自动触发：
    Step 1 - vlm_extract: VLM解析图片内容
    Step 2 - diary_polish: LLM结合图片内容和用户文字润色日记

    完成后状态变为 pending_confirmation，等待用户确认后更新Memory
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)
        self.style_manager = StyleManager()

    def define_steps(self) -> list[str]:
        return ["vlm_extract", "diary_polish"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "vlm_extract":
            return await self._vlm_extract()
        elif step == "diary_polish":
            return await self._diary_polish()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _get_memory_and_media(self) -> tuple[Memory, list[Media]]:
        """获取记忆及其关联的媒体文件"""
        memory_ids = self.generation.memory_ids
        if not memory_ids:
            raise ValueError("No memory_ids found in generation")

        # 获取第一个记忆（单图润色场景）
        stmt_mem = select(Memory).where(Memory.id.in_(memory_ids))
        result_mem = await self.db.execute(stmt_mem)
        memory = result_mem.scalar_one_or_none()

        if not memory:
            raise ValueError(f"Memory not found: {memory_ids}")

        # 获取关联的媒体文件
        stmt_media = (
            select(Media)
            .where(Media.memory_id.in_(memory_ids))
            .order_by(Media.sort_order)
        )
        result_media = await self.db.execute(stmt_media)
        media_files = result_media.scalars().all()

        return memory, media_files

    async def _vlm_extract(self) -> dict[str, Any]:
        """Step 1: VLM解析图片内容"""
        memory, media_files = await self._get_memory_and_media()
        settings = get_settings()

        # 使用纯视觉提取提示词
        vlm_prompt = self.style_manager.get_vlm_visual_prompt()

        # 逐图独立提取
        visual_results = []
        for idx, media in enumerate(media_files):
            if media.file_type == "image":
                # 将相对路径转换为绝对路径
                if os.path.isabs(media.file_path):
                    abs_path = media.file_path
                else:
                    abs_path = os.path.abspath(os.path.join(settings.upload_dir, media.file_path))

                try:
                    metadata = await vlm_service.parse_image(abs_path, vlm_prompt)
                    metadata["_meta"] = {
                        "index": idx,
                        "taken_at": media.taken_at.isoformat() if media.taken_at else None,
                        "sort_order": media.sort_order,
                        "filename": media.original_filename
                    }
                    visual_results.append(metadata)
                except Exception as e:
                    print(f"VLM extract failed for {media.file_path}: {e}")
                    visual_results.append({
                        "scene": "解析失败",
                        "_meta": {
                            "index": idx,
                            "filename": media.original_filename
                        }
                    })

        # 暂存视觉提取结果
        self.generation.vlm_raw_metadata = visual_results
        await self.db.commit()

        return {"visual_results": visual_results}

    async def _diary_polish(self) -> dict[str, Any]:
        """Step 2: LLM结合图片内容和用户文字润色日记"""
        memory, _ = await self._get_memory_and_media()
        visual_results = self.generation.vlm_raw_metadata or []
        user_text = memory.content_text or ""

        # 构建视觉描述
        visual_descriptions = []
        for vr in visual_results:
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
            if parts:
                visual_descriptions.append("; ".join(parts))

        visual_text = "\n".join(visual_descriptions) if visual_descriptions else ""

        # 调用LLM润色日记
        polished_text = await llm_service.polish_diary_with_visual(
            user_text=user_text,
            visual_text=visual_text
        )

        # 存入 generation，供用户确认
        self.generation.user_edited_prompt = user_text  # 保留原文
        self.generation.llm_polished_prompt = polished_text  # 润色结果
        await self.db.commit()

        return {
            "original_text": user_text,
            "polished_text": polished_text,
            "visual_text": visual_text
        }

    async def run(self) -> dict[str, Any]:
        """运行日记润色工作流"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "vlm_extract"
            await self.db.commit()

            # Step 1: VLM解析图片
            await self.update_progress("vlm_extract", 30)
            result = await self._vlm_extract()

            # Step 2: LLM润色日记
            await self.update_progress("diary_polish", 70)
            result = await self._diary_polish()

            # 完成，等待用户确认
            self.generation.status = "pending_confirmation"
            self.generation.progress = 100
            self.generation.current_step = "diary_polish"
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise
