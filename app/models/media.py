from sqlalchemy import Column, String, DateTime, ForeignKey
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
    created_at = Column(DateTime, default=datetime.utcnow)

    memory = relationship("Memory", back_populates="media")
