from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryList

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
    db: AsyncSession = Depends(get_db)
):
    """获取记忆列表"""
    user_id = "00000000-0000-0000-0000-000000000001"

    stmt = select(Memory).where(Memory.user_id == user_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    memories = result.scalars().all()

    return MemoryList(memories=memories, total=len(memories))


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
