from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.memory import Memory
from app.models.media import Media
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryList
from app.schemas.media import MediaResponse
from app.utils.file_utils import normalize_file_path
from app.config import get_settings

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.post("/", response_model=MemoryResponse)
async def create_memory(
    memory_data: MemoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建记忆"""
    # TODO: 从认证中获取user_id，暂时使用测试用户
    user_id = "00000000-0000-0000-0000-000000000001"

    memory = Memory(
        user_id=user_id,
        content_text=memory_data.content_text,
        memory_date=memory_data.memory_date,
        mood_tag=memory_data.mood_tag
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.get("/", response_model=MemoryList)
async def list_memories(
    skip: int = 0,
    limit: int = 20,
    date: Optional[date] = Query(None, description="按日期筛选"),
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db)
):
    """获取记忆列表，支持按日期筛选"""
    user_id = "00000000-0000-0000-0000-000000000001"

    stmt = select(Memory).where(Memory.user_id == user_id)

    # 按单个日期筛选
    if date:
        stmt = stmt.where(Memory.memory_date == date)
    # 按日期范围筛选
    else:
        if start_date:
            stmt = stmt.where(Memory.memory_date >= start_date)
        if end_date:
            stmt = stmt.where(Memory.memory_date <= end_date)

    # 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页查询
    stmt = stmt.order_by(Memory.memory_date.desc(), Memory.created_at.desc())
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    memories = result.scalars().all()

    return MemoryList(memories=memories, total=total)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆详情"""
    stmt = select(Memory).where(Memory.id == memory_id)
    result = await db.execute(stmt)
    memory = result.scalar_one_or_none()

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.get("/{memory_id}/media", response_model=list[MediaResponse])
async def get_memory_media(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取记忆关联的所有媒体文件"""
    settings = get_settings()
    stmt = select(Media).where(Media.memory_id == memory_id).order_by(Media.sort_order)
    result = await db.execute(stmt)
    media_list = result.scalars().all()

    # 规范化路径并添加 URL
    response_list = []
    for media in media_list:
        relative_path = normalize_file_path(media.file_path, settings.upload_dir)
        response_list.append({
            "id": media.id,
            "memory_id": media.memory_id,
            "file_path": relative_path,
            "file_type": media.file_type,
            "original_filename": media.original_filename,
            "taken_at": media.taken_at,
            "sort_order": media.sort_order,
            "created_at": media.created_at,
            "url": f"/uploads/{relative_path}"
        })
    return response_list
