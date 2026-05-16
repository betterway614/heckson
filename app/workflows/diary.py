import os
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
from app.config import get_settings


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
        settings = get_settings()

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
                # 将相对路径转换为绝对路径
                if os.path.isabs(media.file_path):
                    abs_path = media.file_path
                else:
                    abs_path = os.path.abspath(os.path.join(settings.upload_dir, media.file_path))

                metadata = await vlm_service.parse_image(
                    abs_path,
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


class DailyDiaryWorkflow(BaseWorkflow):
    """
    一日漫画工作流

    自动获取当天所有记忆 → VLM逐图解析 → LLM汇总为漫画提示词 → 生成图片
    无需用户手动选择记忆，一键生成当日生活漫画。
    """

    def __init__(self, db: AsyncSession, generation: Generation, memory_date: str):
        super().__init__(db, generation)
        self.memory_date = memory_date
        self.style_manager = StyleManager()

    def define_steps(self) -> list[str]:
        return ["fetch_memories", "vlm_extract", "aggregate_prompt", "img_gen"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "fetch_memories":
            return await self._fetch_memories()
        elif step == "vlm_extract":
            return await self._vlm_extract()
        elif step == "aggregate_prompt":
            return await self._aggregate_prompt()
        elif step == "img_gen":
            return await self._img_gen()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _fetch_memories(self) -> dict[str, Any]:
        """Step 1: 获取当天所有记忆及其媒体文件"""
        from datetime import date as date_type
        from app.models.memory import Memory
        from app.models.media import Media

        # 解析日期
        target_date = date_type.fromisoformat(self.memory_date)

        # 查询当天所有记忆，按创建时间排序
        stmt = (
            select(Memory)
            .where(Memory.user_id == self.generation.user_id)
            .where(Memory.memory_date == target_date)
            .order_by(Memory.created_at.asc())
        )
        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        if not memories:
            raise Exception(f"当天({self.memory_date})没有找到任何记忆")

        # 收集所有记忆的媒体文件
        memory_ids = [m.id for m in memories]
        stmt_media = (
            select(Media)
            .where(Media.memory_id.in_(memory_ids))
            .order_by(Media.taken_at.asc().nullslast(), Media.sort_order.asc())
        )
        result_media = await self.db.execute(stmt_media)
        all_media = result_media.scalars().all()

        # 暂存到 generation 供后续步骤使用
        self.generation.memory_ids = [str(mid) for mid in memory_ids]
        self.generation.vlm_raw_metadata = {
            "memories": [
                {
                    "id": str(m.id),
                    "text": m.content_text or "",
                    "time": m.created_at.isoformat() if m.created_at else "",
                    "mood_tag": m.mood_tag,
                }
                for m in memories
            ],
            "media": [
                {
                    "id": str(m.id),
                    "memory_id": str(m.memory_id),
                    "file_path": m.file_path,
                    "taken_at": m.taken_at.isoformat() if m.taken_at else None,
                }
                for m in all_media
            ]
        }
        await self.db.commit()

        return {
            "memory_count": len(memories),
            "media_count": len(all_media)
        }

    async def _vlm_extract(self) -> dict[str, Any]:
        """Step 2: VLM逐图解析"""
        stored = self.generation.vlm_raw_metadata or {}
        media_list = stored.get("media", [])

        vlm_prompt = self.style_manager.get_vlm_visual_prompt()
        visual_results = []

        for idx, media_info in enumerate(media_list):
            if media_info.get("file_path"):
                try:
                    metadata = await vlm_service.parse_image(
                        media_info["file_path"],
                        vlm_prompt
                    )
                    metadata["_meta"] = {
                        "index": idx,
                        "memory_id": media_info.get("memory_id"),
                        "taken_at": media_info.get("taken_at"),
                    }
                    visual_results.append(metadata)
                except Exception as e:
                    print(f"VLM extract failed for {media_info['file_path']}: {e}")
                    visual_results.append({
                        "scene": "解析失败",
                        "_meta": {
                            "index": idx,
                            "memory_id": media_info.get("memory_id"),
                            "taken_at": media_info.get("taken_at"),
                        }
                    })

        # 更新存储
        stored["visual_results"] = visual_results
        self.generation.vlm_raw_metadata = stored
        await self.db.commit()

        return {"visual_count": len(visual_results)}

    async def _aggregate_prompt(self) -> dict[str, Any]:
        """Step 3: LLM汇总为漫画提示词"""
        from datetime import date as date_type

        stored = self.generation.vlm_raw_metadata or {}
        memories = stored.get("memories", [])
        visual_results = stored.get("visual_results", [])

        # 构建记忆到VLM结果的映射（按 memory_id 关联）
        memory_visual_map = {}
        for vr in visual_results:
            meta = vr.get("_meta", {})
            mem_id = meta.get("memory_id")
            if mem_id:
                if mem_id not in memory_visual_map:
                    memory_visual_map[mem_id] = []
                # 组装可读的视觉描述
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
                memory_visual_map[mem_id].append("; ".join(parts))

        # 组装 all_memories 列表
        all_memories = []
        for mem in memories:
            mem_id = mem.get("id", "")
            visual_parts = memory_visual_map.get(mem_id, [])
            all_memories.append({
                "time": mem.get("time", ""),
                "text": mem.get("text", ""),
                "visual_info": " | ".join(visual_parts) if visual_parts else "",
            })

        # 格式化日期
        target_date = date_type.fromisoformat(self.memory_date)
        date_str = f"{target_date.year}年{target_date.month}月{target_date.day}日"

        # 调用LLM生成漫画提示词
        comic_prompt = await llm_service.generate_daily_diary_prompt(
            memory_date=date_str,
            all_memories=all_memories
        )

        # 保存提示词
        self.generation.user_edited_prompt = comic_prompt
        self.generation.final_prompt = comic_prompt
        self.generation.prompt_confirmed = True
        await self.db.commit()

        return {"comic_prompt": comic_prompt}

    async def _img_gen(self) -> dict[str, Any]:
        """Step 4: 生成漫画图片"""
        final_prompt = self.generation.final_prompt

        # 使用 comic_timeline 风格的 img_prompt 模板
        style = self.style_manager.get_style("comic_timeline")
        img_prompt = style["img_prompt"].format(scene_description=final_prompt)

        # 生成图片
        image_path = await image_service.generate_image(
            prompt=img_prompt,
            generation_id=str(self.generation.id)
        )

        # 创建输出记录
        output = Output(
            generation_id=self.generation.id,
            file_path=image_path,
            file_type="image",
            metadata={
                "final_prompt": final_prompt,
                "style_key": "daily_diary",
                "memory_date": self.memory_date,
            }
        )
        self.db.add(output)
        await self.db.commit()

        return {"output_path": image_path}

    async def run(self) -> dict[str, Any]:
        """运行一日漫画工作流"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "fetch_memories"
            self.generation.progress = 0
            await self.db.commit()

            # Step 1: 获取当天记忆
            await self.update_progress("fetch_memories", 10)
            result = await self._fetch_memories()

            # Step 2: VLM逐图解析
            await self.update_progress("vlm_extract", 30)
            result = await self._vlm_extract()

            # Step 3: LLM汇总提示词
            await self.update_progress("aggregate_prompt", 60)
            result = await self._aggregate_prompt()

            # Step 4: 生成图片
            await self.update_progress("img_gen", 80)
            result = await self._img_gen()

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
