from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, datetime
from uuid import UUID


class MemoryBase(BaseModel):
    content_text: Optional[str] = None
    memory_date: date
    mood_tag: Optional[str] = None


class MemoryCreate(MemoryBase):
    pass


class MemoryResponse(MemoryBase):
    id: UUID
    user_id: UUID
    metadata_json: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryList(BaseModel):
    memories: List[MemoryResponse]
    total: int
