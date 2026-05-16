from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)  # image/audio
    original_filename = Column(String(256))
    taken_at = Column(DateTime, nullable=True)  # 图片拍摄时间 (EXIF)
    sort_order = Column(Integer, default=0)  # 排序序号 (0=最新, 倒序)
    created_at = Column(DateTime, default=datetime.utcnow)

    memory = relationship("Memory", back_populates="media")
