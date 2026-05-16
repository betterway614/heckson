from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class BaseWorkflow(ABC):
    """工作流基类"""

    def __init__(self, db: AsyncSession, generation: Generation):
        self.db = db
        self.generation = generation
        self.steps = self.define_steps()

    @abstractmethod
    def define_steps(self) -> list[str]:
        """定义工作流步骤"""
        pass

    @abstractmethod
    async def execute_step(self, step: str) -> dict[str, Any]:
        """执行单个步骤"""
        pass

    async def update_progress(self, step: str, progress: int, status: str = "processing"):
        """更新进度"""
        self.generation.current_step = step
        self.generation.progress = progress
        self.generation.status = status
        await self.db.commit()

    async def run(self) -> dict[str, Any]:
        """运行完整工作流"""
        try:
            self.generation.status = WorkflowStatus.PROCESSING
            await self.db.commit()

            result = {}
            for i, step in enumerate(self.steps):
                progress = int((i / len(self.steps)) * 100)
                await self.update_progress(step, progress)
                result = await self.execute_step(step)

            self.generation.status = WorkflowStatus.DONE
            self.generation.progress = 100
            self.generation.completed_at = datetime.utcnow()
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = WorkflowStatus.FAILED
            self.generation.error_message = str(e)
            await self.db.commit()
            raise
