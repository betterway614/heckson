import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db, async_session
from app.models.media import Media
from app.models.memory import Memory
from app.models.generation import Generation
from app.schemas.media import MediaResponse, MediaUploadResponse
from app.utils.file_utils import save_upload_file, normalize_file_path
from app.config import get_settings

router = APIRouter(prefix="/api/media", tags=["media"])


def _build_media_response(media: Media) -> dict:
    """构建媒体响应，包含规范化的 URL"""
    settings = get_settings()
    # 规范化文件路径为相对路径
    relative_path = normalize_file_path(media.file_path, settings.upload_dir)
    return {
        "id": media.id,
        "memory_id": media.memory_id,
        "file_path": relative_path,
        "file_type": media.file_type,
        "original_filename": media.original_filename,
        "taken_at": media.taken_at,
        "sort_order": media.sort_order,
        "created_at": media.created_at,
        "url": f"/uploads/{relative_path}"
    }


async def _trigger_diary_polish(memory_id: UUID):
    """触发日记润色工作流（异步）"""
    try:
        async with async_session() as new_db:
            # 获取记忆信息
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await new_db.execute(stmt)
            memory = result.scalar_one_or_none()

            if not memory or not memory.content_text:
                # 没有文字内容，跳过自动润色
                return

            # 创建 Generation 记录
            user_id = "00000000-0000-0000-0000-000000000001"
            generation = Generation(
                user_id=user_id,
                memory_ids=[str(memory_id)],
                type="diary_polish",
                style_key="polished",
                status="processing",
                stage="vlm_extract"
            )
            new_db.add(generation)
            await new_db.commit()
            await new_db.refresh(generation)

            # 启动润色工作流
            from app.workflows.diary_polish import DiaryPolishWorkflow
            workflow = DiaryPolishWorkflow(new_db, generation)
            await workflow.run()

    except Exception as e:
        print(f"Auto diary polish failed: {e}")


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media(
    memory_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传媒体文件，自动触发日记润色"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")

    # 保存文件并提取 EXIF 时间
    file_path, original_filename, taken_at = await save_upload_file(file, "images")

    # 计算 sort_order (倒序: 0=最新, 1=次新, ...)
    # 查询当前 memory 下已有多少张图片
    stmt = select(func.count()).where(Media.memory_id == memory_id)
    result = await db.execute(stmt)
    count = result.scalar() or 0
    sort_order = count  # 新上传的排在最后 (倒序时排最前)

    # 创建记录
    media = Media(
        memory_id=memory_id,
        file_path=file_path,
        file_type="image",
        original_filename=original_filename,
        taken_at=taken_at,
        sort_order=sort_order
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    # 检查是否有文字内容，如果有则自动触发润色
    polish_generation_id = None
    stmt_mem = select(Memory).where(Memory.id == memory_id)
    result_mem = await db.execute(stmt_mem)
    memory = result_mem.scalar_one_or_none()

    if memory and memory.content_text:
        # 异步触发润色工作流
        asyncio.create_task(_trigger_diary_polish(memory_id))
        # 注意：这里无法直接获取 generation_id，因为是异步创建的
        # 前端可以通过查询 generations 列表来获取最新的润色任务

    return MediaUploadResponse(
        media=_build_media_response(media),
        message="上传成功，已自动触发日记润色"
    )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取媒体信息"""
    stmt = select(Media).where(Media.id == media_id)
    result = await db.execute(stmt)
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    return _build_media_response(media)
