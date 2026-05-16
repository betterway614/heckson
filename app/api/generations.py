import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional, List
from datetime import date

from app.database import get_db
from app.models.generation import Generation
from app.models.output import Output
from app.schemas.generation import (
    GenerationCreate, GenerationResponse, GenerationProgress,
    PromptUpdate, PromptPolish, PromptConfirm,
    DiaryPolish, DiaryPolishResponse,
    EmotionExtract,
    ComicPromptGenerate, ComicPromptResponse,
    TextPolishRequest, TextPolishResponse,
    DailyDiaryCreate
)
from app.workflows.diary import VLMWorkflow, ImageGenWorkflow, DailyDiaryWorkflow
from app.workflows.diary_polish import DiaryPolishWorkflow
from app.workflows.video import VideoGenWorkflow
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager
from app.schemas.video import VideoGenerationCreate, VideoScriptUpdate, VIDEO_STYLES
from app.utils.file_utils import normalize_file_path
from app.config import get_settings

router = APIRouter(prefix="/api/generations", tags=["generations"])

style_manager = StyleManager()


@router.get("/polish-styles")
async def list_polish_styles():
    """获取所有日记润色风格列表"""
    return style_manager.list_polish_styles()


@router.post("/polish-text", response_model=TextPolishResponse)
async def polish_text(polish_data: TextPolishRequest):
    """
    独立文本润色（不依赖generation）

    用于用户在输入阶段直接润色文字
    """
    try:
        polished = await llm_service.polish_text(
            text=polish_data.text,
            style_key=polish_data.style_key
        )

        return TextPolishResponse(
            original_text=polish_data.text,
            polished_text=polished,
            style_key=polish_data.style_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"润色失败: {str(e)}")


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


@router.get("/", response_model=List[GenerationResponse])
async def list_generations(
    skip: int = 0,
    limit: int = 20,
    date: Optional[date] = Query(None, description="按日期筛选"),
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db)
):
    """获取生成任务列表"""
    user_id = "00000000-0000-0000-0000-000000000001"

    stmt = select(Generation).where(Generation.user_id == user_id)

    if date:
        stmt = stmt.where(func.date(Generation.created_at) == date)
    else:
        if start_date:
            stmt = stmt.where(func.date(Generation.created_at) >= start_date)
        if end_date:
            stmt = stmt.where(func.date(Generation.created_at) <= end_date)

    stmt = stmt.order_by(Generation.created_at.desc())
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    generations = result.scalars().all()

    return generations


async def _run_vlm_workflow(db: AsyncSession, generation: Generation):
    """运行阶段1：VLM解析 - 使用独立数据库会话"""
    from app.database import async_session
    try:
        async with async_session() as new_db:
            # 重新从数据库加载 generation，避免使用过期的会话对象
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            workflow = VLMWorkflow(new_db, fresh_generation)
            await workflow.run()
    except Exception as e:
        print(f"VLM workflow failed: {e}")
        # 确保失败状态被写入数据库
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"Failed to update generation status: {inner_e}")


# ========== 日记润色（新流程：手动触发） ==========

@router.post("/diary-polish", response_model=GenerationResponse)
async def create_diary_polish(
    generation_data: GenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    手动触发日记润色

    用户上传图片+文字后，可以手动触发润色流程。
    也可以在更新文字后重新触发。
    流程：VLM解析图片 → LLM结合图片和文字润色日记
    """
    user_id = "00000000-0000-0000-0000-000000000001"

    generation = Generation(
        user_id=user_id,
        memory_ids=[str(mid) for mid in generation_data.memory_ids],
        type="diary_polish",
        style_key="polished",
        status="processing",
        stage="vlm_extract"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动日记润色工作流
    asyncio.create_task(_run_diary_polish_workflow(db, generation))

    return generation


async def _run_diary_polish_workflow(db: AsyncSession, generation: Generation):
    """运行日记润色工作流 - 使用独立数据库会话"""
    from app.database import async_session
    try:
        async with async_session() as new_db:
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            workflow = DiaryPolishWorkflow(new_db, fresh_generation)
            await workflow.run()
    except Exception as e:
        print(f"Diary polish workflow failed: {e}")
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"Failed to update generation status: {inner_e}")


# ========== 一日漫画（必须在动态路由之前） ==========

@router.post("/daily-diary", response_model=GenerationResponse)
async def create_daily_diary(
    data: DailyDiaryCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    一键生成一日漫画

    自动获取当天所有记忆，按时间顺序汇总，生成一张生活漫画。
    流程：获取记忆 → VLM逐图解析 → LLM汇总漫画提示词 → 生成图片

    参数：
    - memory_date: 日期（YYYY-MM-DD格式）
    """
    user_id = "00000000-0000-0000-0000-000000000001"

    # 创建 Generation 记录
    generation = Generation(
        user_id=user_id,
        memory_ids=[],  # 工作流会自动填充
        type="daily_diary",
        style_key="comic_timeline",
        status="processing",
        stage="fetch_memories"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动一日漫画工作流
    asyncio.create_task(_run_daily_diary_workflow(db, generation, data.memory_date))

    return generation


async def _run_daily_diary_workflow(db: AsyncSession, generation: Generation, memory_date: str):
    """运行一日漫画工作流 - 使用独立数据库会话"""
    from app.database import async_session
    try:
        async with async_session() as new_db:
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            workflow = DailyDiaryWorkflow(new_db, fresh_generation, memory_date)
            await workflow.run()
    except Exception as e:
        print(f"Daily diary workflow failed: {e}")
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"Failed to update generation status: {inner_e}")


# ========== 视频生成路由（必须在动态路由之前） ==========

@router.get("/video-styles")
async def list_video_styles():
    """获取所有视频风格列表"""
    return VIDEO_STYLES


@router.post("/video", response_model=GenerationResponse)
async def create_video_generation(
    video_data: VideoGenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建视频生成任务

    参数：
    - start_date: 开始日期
    - end_date: 结束日期
    - style: 视频风格（cinematic/documentary/warm_memory/vibrant）
    - resolution: 视频分辨率（1280x720/720x1280/1920x1080/1080x1920）
    """
    user_id = "00000000-0000-0000-0000-000000000001"

    # 创建 Generation 记录
    generation = Generation(
        user_id=user_id,
        memory_ids=[],  # 视频生成不依赖特定记忆ID
        type="video",
        style_key=video_data.style,
        video_params={
            "resolution": video_data.resolution,
            "duration": 15,
            "style": video_data.style,
            "date_range": {
                "start": video_data.start_date.isoformat(),
                "end": video_data.end_date.isoformat()
            }
        },
        video_resolution=video_data.resolution,
        video_duration=15,
        video_style=video_data.style,
        status="processing",
        stage="script_gen"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动阶段1：脚本生成
    asyncio.create_task(_run_video_script_workflow(db, generation))

    return generation


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

    if generation.status not in ("pending_confirmation", "done"):
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
    """运行阶段2：图片生成 - 使用独立数据库会话"""
    from app.database import async_session
    print(f"[IMG_GEN] Starting workflow for generation {generation.id}")
    try:
        async with async_session() as new_db:
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            print(f"[IMG_GEN] Loaded generation, status: {fresh_generation.status}")
            workflow = ImageGenWorkflow(new_db, fresh_generation)
            print("[IMG_GEN] Running workflow...")
            await workflow.run()
            print(f"[IMG_GEN] Workflow completed successfully")
    except Exception as e:
        print(f"[IMG_GEN] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"[IMG_GEN] Failed to update status: {inner_e}")


@router.get("/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: UUID,
):
    """SSE推送生成进度 - 使用独立数据库会话，避免会话在流式响应期间关闭"""
    from app.database import async_session
    from datetime import datetime, timedelta

    MAX_POLL_SECONDS = 600      # 最大轮询时间：10分钟
    INITIAL_INTERVAL = 2        # 初始轮询间隔：2秒（避免过于频繁）
    MAX_INTERVAL = 10           # 最大轮询间隔：10秒
    STALE_THRESHOLD_MINUTES = 5 # 任务卡住阈值：5分钟无更新

    async def event_generator():
        start_time = asyncio.get_event_loop().time()
        poll_count = 0
        interval = INITIAL_INTERVAL
        last_progress = -1
        last_progress_time = datetime.utcnow()

        while True:
            # 检查是否超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > MAX_POLL_SECONDS:
                error_data = json.dumps({"error": "轮询超时，请刷新页面重试"})
                yield f"event: error\ndata: {error_data}\n\n"
                break

            async with async_session() as db:
                stmt = select(Generation).where(Generation.id == generation_id)
                result = await db.execute(stmt)
                generation = result.scalar_one_or_none()

                if not generation:
                    error_data = json.dumps({"error": "Generation not found"})
                    yield f"event: error\ndata: {error_data}\n\n"
                    break

                # 检测任务是否卡住
                if generation.status == "processing":
                    # 检查进度是否有变化
                    if generation.progress != last_progress:
                        last_progress = generation.progress
                        last_progress_time = datetime.utcnow()
                    elif datetime.utcnow() - last_progress_time > timedelta(minutes=STALE_THRESHOLD_MINUTES):
                        # 任务超过5分钟没有进度更新，标记为失败
                        generation.status = "failed"
                        generation.error_message = "任务执行超时，请重试"
                        await db.commit()
                        error_data = json.dumps({
                            "error": "任务执行超时",
                            "generation_id": str(generation.id)
                        })
                        yield f"event: error\ndata: {error_data}\n\n"
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
                json_data = json.dumps(progress_data, ensure_ascii=False)
                yield f"event: progress\ndata: {json_data}\n\n"

                # 如果完成或失败，结束
                if generation.status in ["done", "failed", "pending_confirmation"]:
                    yield f"event: complete\ndata: {json_data}\n\n"
                    break

            # 指数退避：每5次轮询后增加间隔，更平滑的退避
            poll_count += 1
            if poll_count % 5 == 0 and interval < MAX_INTERVAL:
                interval = min(interval * 1.5, MAX_INTERVAL)

            await asyncio.sleep(interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ========== 新增：日记润色确认（新流程） ==========

@router.post("/{generation_id}/confirm-diary-polish")
async def confirm_diary_polish(
    generation_id: UUID,
    confirm_data: PromptConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    确认日记润色结果，更新 Memory 内容

    用户确认润色后的日记文本后，将其保存到对应的 Memory 中
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.type != "diary_polish":
        raise HTTPException(status_code=400, detail="Generation is not a diary_polish type")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for confirmation")

    # 获取对应的 Memory
    memory_ids = generation.memory_ids
    if not memory_ids:
        raise HTTPException(status_code=400, detail="No memory_ids found in generation")

    from app.models.memory import Memory
    stmt_mem = select(Memory).where(Memory.id.in_(memory_ids))
    result_mem = await db.execute(stmt_mem)
    memory = result_mem.scalar_one_or_none()

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # 更新 Memory 内容
    memory.content_text = confirm_data.final_prompt

    # 更新 Generation 状态
    generation.status = "done"
    generation.progress = 100
    generation.prompt_confirmed = True
    from datetime import datetime
    generation.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(memory)

    return {
        "memory_id": memory.id,
        "content_text": memory.content_text,
        "generation_id": generation.id,
        "message": "日记已保存"
    }


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


# ========== 获取生成结果 ==========

@router.get("/{generation_id}/outputs")
async def get_generation_outputs(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取生成任务的输出文件列表"""
    settings = get_settings()
    stmt = select(Output).where(Output.generation_id == generation_id)
    result = await db.execute(stmt)
    outputs = result.scalars().all()

    return [
        {
            "id": str(output.id),
            "file_path": normalize_file_path(output.file_path, settings.output_dir),
            "file_type": output.file_type,
            "url": f"/outputs/{normalize_file_path(output.file_path, settings.output_dir)}",
            "created_at": output.created_at.isoformat() if output.created_at else None
        }
        for output in outputs
    ]


# ========== 视频脚本和确认路由 ==========

@router.get("/{generation_id}/video-script")
async def get_video_script(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取视频脚本"""
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.type != "video":
        raise HTTPException(status_code=400, detail="Generation is not a video type")

    return {
        "generation_id": str(generation.id),
        "script": generation.video_script,
        "status": generation.status
    }


@router.put("/{generation_id}/video-script", response_model=GenerationResponse)
async def update_video_script(
    generation_id: UUID,
    script_data: VideoScriptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新视频脚本（用户编辑）"""
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for script editing")

    generation.video_script = script_data.script
    await db.commit()
    await db.refresh(generation)

    return generation


@router.post("/{generation_id}/confirm-video", response_model=GenerationResponse)
async def confirm_video_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    确认视频脚本，触发阶段2：视频生成

    用户确认脚本后，调用 wan2.7 生成视频
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for confirmation")

    # 更新状态
    generation.status = "processing"
    generation.stage = "video_gen"
    await db.commit()

    # 异步启动阶段2：视频生成
    asyncio.create_task(_run_video_gen_workflow(db, generation))

    await db.refresh(generation)
    return generation


# ========== 视频生成辅助函数 ==========

async def _run_video_script_workflow(db: AsyncSession, generation: Generation):
    """运行阶段1：脚本生成 - 使用独立数据库会话"""
    from app.database import async_session
    try:
        async with async_session() as new_db:
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            workflow = VideoGenWorkflow(new_db, fresh_generation)
            await workflow.run_script_gen()
    except Exception as e:
        print(f"Video script workflow failed: {e}")
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"Failed to update generation status: {inner_e}")


async def _run_video_gen_workflow(db: AsyncSession, generation: Generation):
    """运行阶段2：视频生成 - 使用独立数据库会话"""
    from app.database import async_session
    try:
        async with async_session() as new_db:
            stmt = select(Generation).where(Generation.id == generation.id)
            result = await new_db.execute(stmt)
            fresh_generation = result.scalar_one()
            workflow = VideoGenWorkflow(new_db, fresh_generation)
            await workflow.run_video_gen()
    except Exception as e:
        print(f"Video generation workflow failed: {e}")
        try:
            async with async_session() as fail_db:
                stmt = select(Generation).where(Generation.id == generation.id)
                result = await fail_db.execute(stmt)
                gen = result.scalar_one()
                gen.status = "failed"
                gen.error_message = str(e)
                await fail_db.commit()
        except Exception as inner_e:
            print(f"Failed to update generation status: {inner_e}")
