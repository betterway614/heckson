import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.generation import Generation
from app.schemas.generation import GenerationCreate, GenerationResponse, GenerationProgress
from app.workflows.diary import DiaryWorkflow

router = APIRouter(prefix="/api/generations", tags=["generations"])


@router.post("/", response_model=GenerationResponse)
async def create_generation(
    generation_data: GenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建生成任务"""
    user_id = "00000000-0000-0000-0000-000000000001"

    generation = Generation(
        user_id=user_id,
        memory_ids=[str(mid) for mid in generation_data.memory_ids],
        type=generation_data.type,
        style_key=generation_data.style_key,
        status="pending"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动工作流
    asyncio.create_task(_run_workflow(db, generation))

    return generation


async def _run_workflow(db: AsyncSession, generation: Generation):
    """运行工作流"""
    try:
        workflow = DiaryWorkflow(db, generation)
        await workflow.run()
    except Exception as e:
        print(f"Workflow failed: {e}")


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取生成任务状态"""
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    return generation


@router.get("/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """SSE推送生成进度"""
    async def event_generator():
        while True:
            stmt = select(Generation).where(Generation.id == generation_id)
            result = await db.execute(stmt)
            generation = result.scalar_one_or_none()

            if not generation:
                yield f"event: error\ndata: {{\"error\": \"Generation not found\"}}\n\n"
                break

            # 发送进度
            progress_data = {
                "generation_id": str(generation.id),
                "status": generation.status,
                "progress": generation.progress,
                "current_step": generation.current_step
            }
            yield f"event: progress\ndata: {progress_data}\n\n"

            # 如果完成或失败，结束
            if generation.status in ["done", "failed"]:
                yield f"event: complete\ndata: {progress_data}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
