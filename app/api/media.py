from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.models.media import Media
from app.schemas.media import MediaResponse
from app.utils.file_utils import save_upload_file

router = APIRouter(prefix="/api/media", tags=["media"])


@router.post("/upload", response_model=MediaResponse)
async def upload_media(
    memory_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """上传媒体文件"""
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

    return media


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

    return media
