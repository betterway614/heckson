from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.models.generation import Generation
from app.models.memory import Memory
from app.workflows.base import BaseWorkflow
from app.services.llm_service import llm_service
from app.services.video_service import video_service
from app.schemas.video import VIDEO_STYLES


class VideoGenWorkflow(BaseWorkflow):
    """
    视频生成工作流（两阶段）

    阶段1：脚本生成（script_gen）
      - 读取时间范围内的记忆
      - 按 memory_date 排序
      - LLM 生成视频脚本
      - 状态变为 pending_confirmation

    阶段2：视频生成（video_gen）
      - 用户确认/编辑脚本
      - 调用 wan2.7 API
      - 下载视频文件
      - 状态变为 done
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)

    def define_steps(self) -> list[str]:
        return ["script_gen", "video_gen"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "script_gen":
            return await self._script_gen()
        elif step == "video_gen":
            return await self._video_gen()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _get_memories_in_range(self) -> list[Memory]:
        """获取时间范围内的记忆"""
        date_range = self.generation.video_params.get("date_range", {})
        start_date = date_range.get("start")
        end_date = date_range.get("end")

        if not start_date or not end_date:
            raise ValueError("Missing date_range in video_params")

        stmt = (
            select(Memory)
            .where(Memory.user_id == self.generation.user_id)
            .where(Memory.memory_date >= start_date)
            .where(Memory.memory_date <= end_date)
            .order_by(Memory.memory_date)
        )

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        if not memories:
            raise ValueError(f"No memories found in date range: {start_date} to {end_date}")

        return list(memories)

    async def _script_gen(self) -> dict[str, Any]:
        """阶段1：生成视频脚本"""
        # 1. 获取时间范围内的记忆
        memories = await self._get_memories_in_range()

        # 2. 调用 LLM 生成视频脚本
        script = await llm_service.generate_video_script(
            memories=memories,
            style=self.generation.video_style
        )

        # 3. 保存脚本
        self.generation.video_script = script
        await self.db.commit()

        return {"script": script, "memory_count": len(memories)}

    async def _video_gen(self) -> dict[str, Any]:
        """阶段2：生成视频"""
        # 1. 获取用户确认的脚本
        script = self.generation.video_script
        if not script:
            raise ValueError("Video script not found")

        # 2. 构建完整提示词
        style_info = VIDEO_STYLES.get(self.generation.video_style, {})
        prompt_prefix = style_info.get("prompt_prefix", "")
        full_prompt = f"{prompt_prefix}{script}"

        # 3. 调用视频生成服务
        video_url = await video_service.generate_video(
            prompt=full_prompt,
            resolution=self.generation.video_resolution,
            duration=self.generation.video_duration,
            generation_id=str(self.generation.id)
        )

        # 4. 保存视频路径
        self.generation.video_url = video_url
        await self.db.commit()

        return {"video_url": video_url}

    async def run_script_gen(self) -> dict[str, Any]:
        """运行阶段1：脚本生成"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "script_gen"
            await self.db.commit()

            # 执行脚本生成
            await self.update_progress("script_gen", 50)
            result = await self._script_gen()

            # 完成，等待用户确认
            self.generation.status = "pending_confirmation"
            self.generation.progress = 100
            self.generation.current_step = "script_gen"
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise

    async def run_video_gen(self) -> dict[str, Any]:
        """运行阶段2：视频生成"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "video_gen"
            self.generation.progress = 0
            await self.db.commit()

            # 执行视频生成
            await self.update_progress("video_gen", 50)
            result = await self._video_gen()

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
