import asyncio
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from uuid import UUID

from app.database import async_session, get_db
from app.models.generation import Generation
from app.schemas.generation import (
    GenerationCreate, GenerationResponse, GenerationProgress,
    PromptUpdate, PromptPolish, PromptConfirm,
    DiaryPolish, DiaryPolishResponse,
    EmotionExtract,
    ComicPromptGenerate, ComicPromptResponse
)
from app.workflows.diary import VLMWorkflow, ImageGenWorkflow
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager

router = APIRouter(prefix="/api/generations", tags=["generations"])

style_manager = StyleManager()


@router.get("/polish-styles")
async def list_polish_styles():
    """获取所有日记润色风格列表"""
    return style_manager.list_polish_styles()


@router.get("/", response_model=list[GenerationResponse])
async def list_generations(
    skip: int = 0,
    limit: int = 20,
    date: Optional[date] = Query(None, description="按创建日期筛选"),
    db: AsyncSession = Depends(get_db)
):
    """获取生成任务列表，支持按创建日期筛选"""
    user_id = "00000000-0000-0000-0000-000000000001"

    stmt = select(Generation).where(Generation.user_id == user_id)
    if date:
        stmt = stmt.where(func.date(Generation.created_at) == date)

    stmt = stmt.order_by(Generation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


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
    asyncio.create_task(_run_vlm_workflow(generation.id))

    return generation


async def _run_vlm_workflow(generation_id: UUID):
    """运行阶段1：VLM解析"""
    try:
        async with async_session() as db:
            stmt = select(Generation).where(Generation.id == generation_id)
            result = await db.execute(stmt)
            generation = result.scalar_one_or_none()
            if not generation:
                return
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
    asyncio.create_task(_run_img_gen_workflow(generation.id))

    await db.refresh(generation)
    return generation


async def _run_img_gen_workflow(generation_id: UUID):
    """运行阶段2：图片生成"""
    try:
        async with async_session() as db:
            stmt = select(Generation).where(Generation.id == generation_id)
            result = await db.execute(stmt)
            generation = result.scalar_one_or_none()
            if not generation:
                return
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
            yield f"event: progress\ndata: {json.dumps(progress_data, default=str, ensure_ascii=False)}\n\n"

            # 如果完成或失败，结束
            if generation.status in ["done", "failed", "pending_confirmation"]:
                yield f"event: complete\ndata: {json.dumps(progress_data, default=str, ensure_ascii=False)}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ========== 新增：日记润色 ==========

@router.post("/{generation_id}/polish-diary", response_model=DiaryPolishResponse)
async def polish_diary(
    generation_id: UUID,
    polish_data: DiaryPolish,
    db: AsyncSession = Depends(get_db)
):
    """
    日记润色 - 支持4种风格

    - polished: 润色稿（文学性/私密手账）
    - douyin: 抖音文案（强情绪/神反转）
    - xiaohongshu: 小红书（种草/高颜值）
    - moments: 朋友圈（克制/生活化）
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # 获取风格信息
    from app.templates.styles import POLISH_STYLES
    style_info = POLISH_STYLES.get(polish_data.style_key)
    if not style_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid polish style: {polish_data.style_key}. "
                   f"Available: {list(POLISH_STYLES.keys())}"
        )

    # 调用LLM润色
    polished = await llm_service.polish_diary(
        diary_text=polish_data.diary_text,
        style_key=polish_data.style_key
    )

    # 保存润色结果到generation
    generation.llm_polished_prompt = polished
    await db.commit()

    return DiaryPolishResponse(
        original_text=polish_data.diary_text,
        polished_text=polished,
        style_key=polish_data.style_key,
        style_name=style_info["name"]
    )


# ========== 新增：情绪提取 ==========

@router.post("/{generation_id}/extract-emotion")
async def extract_emotion(
    generation_id: UUID,
    emotion_data: EmotionExtract,
    db: AsyncSession = Depends(get_db)
):
    """
    情绪提取 - 分析日记内容，返回结构化情绪标签

    返回JSON格式：
    - primary_emotion: 主要情绪
    - intensity: 情绪强度(1-10)
    - secondary_emotion: 次要情绪
    - bgm_vibe: 推荐BGM风格
    - color_palette: 推荐色调
    - weather_mood: 天气氛围
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    emotion_result = await llm_service.extract_emotion(
        diary_text=emotion_data.diary_text
    )

    return emotion_result


# ========== 新增：漫画分镜生成 ==========

@router.post("/{generation_id}/generate-comic-prompt", response_model=ComicPromptResponse)
async def generate_comic_prompt(
    generation_id: UUID,
    comic_data: ComicPromptGenerate,
    db: AsyncSession = Depends(get_db)
):
    """
    漫画分镜提示词生成

    - comic_shuangwen: 高光爽文（热血少年漫/戏剧性冲突）
    - comic_zhiyu: 治愈温馨（吉卜力/松弛感）
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    style = style_manager.get_style(comic_data.style_key)
    if not style or not style.get("comic_prompt_key"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid comic style: {comic_data.style_key}"
        )

    # 生成漫画分镜提示词
    comic_prompt = await llm_service.generate_comic_prompt(
        diary_text=comic_data.diary_text,
        style_key=comic_data.style_key
    )

    # 更新generation的final_prompt
    generation.final_prompt = comic_prompt
    await db.commit()

    return ComicPromptResponse(
        diary_text=comic_data.diary_text,
        comic_prompt=comic_prompt,
        style_key=comic_data.style_key,
        style_name=style["name"]
    )
