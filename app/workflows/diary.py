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


class DiaryWorkflow(BaseWorkflow):
    """日记生成工作流"""

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)
        self.style_manager = StyleManager()
        self.style = self.style_manager.get_style(generation.style_key)

    def define_steps(self) -> list[str]:
        return ["vlm_parse", "llm_script", "img_gen", "compose"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "vlm_parse":
            return await self._vlm_parse()
        elif step == "llm_script":
            return await self._llm_script()
        elif step == "img_gen":
            return await self._img_gen()
        elif step == "compose":
            return await self._compose()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _vlm_parse(self) -> dict[str, Any]:
        """Step 1: VLM解析"""
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
        await self.db.commit()

        return {"metadata": all_metadata}

    async def _llm_script(self) -> dict[str, Any]:
        """Step 2: LLM生成文案"""
        # 获取第一个Memory的metadata
        memory_id = self.generation.memory_ids[0]
        stmt = select(Memory).where(Memory.id == memory_id)
        result = await self.db.execute(stmt)
        memory = result.scalar_one()

        # 生成文案
        script = await llm_service.generate_script(
            metadata=memory.metadata_json,
            style_prompt=self.style["llm_prompt"],
            user_mood=memory.mood_tag or "",
            memory_date=str(memory.memory_date)
        )

        return script

    async def _img_gen(self) -> dict[str, Any]:
        """Step 3: 图像生成"""
        # 获取上一步的脚本
        script = await self._llm_script()
        scene_description = script.get("scene_description", "")

        # 构建图片生成提示词
        img_prompt = self.style["img_prompt"].format(
            scene_description=scene_description
        )

        # 生成图片
        image_path = await image_service.generate_image(
            prompt=img_prompt,
            generation_id=str(self.generation.id)
        )

        return {"image_path": image_path, "script": script}

    async def _compose(self) -> dict[str, Any]:
        """Step 4: 合成输出"""
        # 获取图片和脚本
        img_result = await self._img_gen()
        image_path = img_result["image_path"]
        script = img_result["script"]

        # TODO: 使用Pillow添加文字气泡
        # 这里简化处理，直接保存为最终输出
        output = Output(
            generation_id=self.generation.id,
            file_path=image_path,
            file_type="image",
            metadata={
                "caption": script.get("caption", ""),
                "bubble_text": script.get("bubble_text", "")
            }
        )
        self.db.add(output)
        await self.db.commit()

        return {"output_path": image_path}
