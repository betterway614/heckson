from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class GenerationCreate(BaseModel):
    memory_ids: List[UUID]
    type: str = "diary"
    style_key: str


class GenerationResponse(BaseModel):
    id: UUID
    user_id: UUID
    memory_ids: List[UUID]
    type: str
    style_key: str
    status: str
    progress: int
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationProgress(BaseModel):
    generation_id: UUID
    status: str
    progress: int
    current_step: Optional[str] = None
