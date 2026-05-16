from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    阶段1：VLM解析工作流

    解析图片，提取元数据，完成后状态变为pending_confirmation
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)
        self.style_manager = StyleManager()
        self.style = self.style_manager.get_style(generation.style_key)

    def define_steps(self) -> list[str]:
        return ["vlm_parse"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "vlm_parse":
            return await self._vlm_parse()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _vlm_parse(self) -> dict[str, Any]:
        """VLM解析图片"""
        # 获取关联的媒体文件
        memory_ids = self.generation.memory_ids
        stmt = select(Media).where(Media.memory_id.in_(memory_ids))
        result = await self.db.execute(stmt)
        media_files = result.scalars().all()

        # 解析每张图片
        all_metadata = []
        for media in media_files:
            if media.file_type == "image":
                metadata = await vlm_service.parse_image(
                    media.file_path,
                    self.style["vlm_prompt"]
                )
                all_metadata.append(metadata)

        # 更新Memory的metadata_json
        stmt = select(Memory).where(Memory.id.in_(memory_ids))
        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        for memory in memories:
            memory.metadata_json = all_metadata

        # 更新Generation的vlm_raw_metadata
        self.generation.vlm_raw_metadata = all_metadata

        await self.db.commit()

        return {"metadata": all_metadata}

    async def run(self) -> dict[str, Any]:
        """运行VLM解析，完成后设置状态为pending_confirmation"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "vlm_parse"
            await self.db.commit()

            result = await self.execute_step("vlm_parse")

            # VLM解析完成，等待用户确认
            self.generation.status = "pending_confirmation"
            self.generation.progress = 100
            self.generation.current_step = "vlm_parse"
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
