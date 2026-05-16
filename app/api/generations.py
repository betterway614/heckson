import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.generation import Generation
from app.schemas.generation import (
    GenerationCreate, GenerationResponse, GenerationProgress,
    PromptUpdate, PromptPolish, PromptConfirm
)
from app.workflows.diary import VLMWorkflow, ImageGenWorkflow
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager

router = APIRouter(prefix="/api/generations", tags=["generations"])

style_manager = StyleManager()


@router.post("/", response_model=GenerationResponse)
async def create_generation(
    generation_data: GenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建生成任务 - 阶段1：VLM解析

    创建任务后自动触发VLM解析，解析完成后状态变为pending_confirmation
    """
    user_id = "00000000-0000-0000-0000-000000000001"

    generation = Generation(
        user_id=user_id,
        memory_ids=[str(mid) for mid in generation_data.memory_ids],
        type=generation_data.type,
        style_key=generation_data.style_key,
        status="processing",
        stage="vlm_parse"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动阶段1：VLM解析
    asyncio.create_task(_run_vlm_workflow(db, generation))

    return generation


async def _run_vlm_workflow(db: AsyncSession, generation: Generation):
    """运行阶段1：VLM解析"""
    try:
        workflow = VLMWorkflow(db, generation)
        await workflow.run()
    except Exception as e:
        print(f"VLM workflow failed: {e}")


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


@router.put("/{generation_id}/prompt", response_model=GenerationResponse)
async def update_prompt(
    generation_id: UUID,
    prompt_data: PromptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户编辑的提示词

    用户查看VLM解析结果后，可以自定义编辑提示词
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for prompt editing")

    generation.user_edited_prompt = prompt_data.user_edited_prompt
    await db.commit()
    await db.refresh(generation)

    return generation


@router.post("/{generation_id}/polish", response_model=GenerationResponse)
async def polish_prompt(
    generation_id: UUID,
    polish_data: PromptPolish,
    db: AsyncSession = Depends(get_db)
):
    """
    LLM润色提示词（可选功能）

    用户可以选择让LLM润色自己编辑的提示词
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for prompt polishing")

    # 获取风格模板
    style = style_manager.get_style(generation.style_key)
    if not style:
        raise HTTPException(status_code=400, detail="Invalid style key")

    # 调用LLM润色
    polished = await llm_service.polish_prompt(
        prompt=polish_data.prompt,
        style_name=style["name"]
    )

    generation.llm_polished_prompt = polished
    await db.commit()
    await db.refresh(generation)

    return generation


@router.post("/{generation_id}/confirm", response_model=GenerationResponse)
async def confirm_prompt(
    generation_id: UUID,
    confirm_data: PromptConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    确认提示词 - 触发阶段2：图片生成

    用户确认最终提示词后，触发图片生成工作流
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for confirmation")

    # 设置确认信息
    generation.final_prompt = confirm_data.final_prompt
    generation.prompt_confirmed = True
    generation.status = "processing"
    generation.stage = "img_gen"
    await db.commit()

    # 异步启动阶段2：图片生成
    asyncio.create_task(_run_img_gen_workflow(db, generation))

    await db.refresh(generation)
    return generation


async def _run_img_gen_workflow(db: AsyncSession, generation: Generation):
    """运行阶段2：图片生成"""
    try:
        workflow = ImageGenWorkflow(db, generation)
        await workflow.run()
    except Exception as e:
        print(f"Image generation workflow failed: {e}")


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
                "stage": generation.stage,
                "progress": generation.progress,
                "current_step": generation.current_step,
                "vlm_raw_metadata": generation.vlm_raw_metadata,
                "user_edited_prompt": generation.user_edited_prompt,
                "llm_polished_prompt": generation.llm_polished_prompt,
                "final_prompt": generation.final_prompt
            }
            yield f"event: progress\ndata: {progress_data}\n\n"

            # 如果完成或失败，结束
            if generation.status in ["done", "failed", "pending_confirmation"]:
                yield f"event: complete\ndata: {progress_data}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
