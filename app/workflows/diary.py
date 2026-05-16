from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.generation import Generation
from app.models.memory import Memory
from app.models.media import Media
from app.models.output import Output
from app.workflows.base import BaseWorkflow
from app.services.vlm_service import vlm_service
from app.services.llm_service import llm_service
from app.services.img_service import image_service
from app.templates.styles import StyleManager


class VLMWorkflow(BaseWorkflow):
    """
    阶段1：VLM解析工作流（策略B：两步分离）

    Step 1 - vlm_extract: 纯视觉提取（不带用户文本，逐图独立）
    Step 2 - diary_generate: LLM汇总（VLM结果 + 用户文本 → 日记正文）
    完成后状态变为 pending_confirmation
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)
        self.style_manager = StyleManager()
        self.style = self.style_manager.get_style(generation.style_key)

    def define_steps(self) -> list[str]:
        return ["vlm_extract", "diary_generate"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "vlm_extract":
            return await self._vlm_extract()
        elif step == "diary_generate":
            return await self._diary_generate()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _get_user_text(self) -> str:
        """获取用户文字内容"""
        memory_ids = self.generation.memory_ids
        stmt_mem = select(Memory).where(Memory.id.in_(memory_ids))
        result_mem = await self.db.execute(stmt_mem)
        memories = result_mem.scalars().all()
        return " ".join([m.content_text or "" for m in memories]).strip()

    async def _vlm_extract(self) -> dict[str, Any]:
        """Step 1: 纯视觉提取 - VLM只看图，不带用户文本"""
        memory_ids = self.generation.memory_ids
        # 按 taken_at 排序（早→晚），没有时间的按 sort_order
        stmt = (
            select(Media)
            .where(Media.memory_id.in_(memory_ids))
            .order_by(Media.sort_order)
        )
        result = await self.db.execute(stmt)
        media_files = result.scalars().all()

        # 使用纯视觉提取提示词（不含用户文本）
        vlm_prompt = self.style_manager.get_vlm_visual_prompt()

        # 逐图独立提取，附带时间元数据
        visual_results = []
        for idx, media in enumerate(media_files):
            if media.file_type == "image":
                metadata = await vlm_service.parse_image(
                    media.file_path,
                    vlm_prompt
                )
                # 附带时间元数据
                metadata["_meta"] = {
                    "index": idx,
                    "taken_at": media.taken_at.isoformat() if media.taken_at else None,
                    "sort_order": media.sort_order,
                    "filename": media.original_filename
                }
                visual_results.append(metadata)

        # 暂存视觉提取结果
        self.generation.vlm_raw_metadata = visual_results
        await self.db.commit()

        return {"visual_results": visual_results}

    async def _diary_generate(self) -> dict[str, Any]:
        """Step 2: 日记汇总 - LLM融合VLM结果 + 用户文本"""
        visual_results = self.generation.vlm_raw_metadata or []
        user_text = await self._get_user_text()

        # 调用LLM汇总生成日记正文
        diary_text = await llm_service.aggregate_diary(
            visual_results=visual_results,
            user_text=user_text
        )

        # 存入 generation，供用户确认
        self.generation.user_edited_prompt = diary_text
        await self.db.commit()

        return {"diary_text": diary_text, "user_text": user_text}

    async def run(self) -> dict[str, Any]:
        """运行VLM解析，完成后设置状态为pending_confirmation"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "vlm_extract"
            await self.db.commit()

            # Step 1: 纯视觉提取
            await self.update_progress("vlm_extract", 30)
            result = await self._vlm_extract()

            # Step 2: 日记汇总
            await self.update_progress("diary_generate", 70)
            result = await self._diary_generate()

            # 完成，等待用户确认
            self.generation.status = "pending_confirmation"
            self.generation.progress = 100
            self.generation.current_step = "diary_generate"
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise


class ImageGenWorkflow(BaseWorkflow):
    """
    阶段2：图片生成工作流

    用户确认提示词后，生成图片
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)
        self.style_manager = StyleManager()
        self.style = self.style_manager.get_style(generation.style_key)

    def define_steps(self) -> list[str]:
        return ["img_gen", "compose"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "img_gen":
            return await self._img_gen()
        elif step == "compose":
            return await self._compose()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _img_gen(self) -> dict[str, Any]:
        """图片生成"""
        # 获取用户确认的提示词
        final_prompt = self.generation.final_prompt

        # 构建图片生成提示词
        img_prompt = self.style["img_prompt"].format(
            scene_description=final_prompt
        )

        # 生成图片
        image_path = await image_service.generate_image(
            prompt=img_prompt,
            generation_id=str(self.generation.id)
        )

        return {"image_path": image_path}

    async def _compose(self) -> dict[str, Any]:
        """合成输出"""
        img_result = await self._img_gen()
        image_path = img_result["image_path"]

        # 创建输出记录
        output = Output(
            generation_id=self.generation.id,
            file_path=image_path,
            file_type="image",
            metadata={
                "final_prompt": self.generation.final_prompt,
                "style_key": self.generation.style_key
            }
        )
        self.db.add(output)
        await self.db.commit()

        return {"output_path": image_path}

    async def run(self) -> dict[str, Any]:
        """运行图片生成工作流"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "img_gen"
            self.generation.progress = 0
            await self.db.commit()

            # Step 1: 图片生成
            await self.update_progress("img_gen", 50)
            result = await self.execute_step("compose")

            # 完成
            self.generation.status = "done"
            self.generation.progress = 100
            self.generation.current_step = "done"
            from datetime import datetime
            self.generation.completed_at = datetime.utcnow()
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise
