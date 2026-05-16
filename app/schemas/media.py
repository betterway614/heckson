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
    taken_at: Optional[datetime] = None
    sort_order: int = 0
    created_at: datetime
    url: Optional[str] = None  # URL 友好的访问路径

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    """媒体上传响应（包含自动生成的润色任务）"""
    media: MediaResponse
    polish_generation_id: Optional[UUID] = None  # 自动触发的润色任务ID
    message: str = "上传成功"
