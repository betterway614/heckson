from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class MediaResponse(BaseModel):
    id: UUID
    memory_id: UUID
    file_path: str
    file_type: str
    original_filename: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
