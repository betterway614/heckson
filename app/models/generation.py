from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Generation(Base):
    __tablename__ = "generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    memory_ids = Column(JSONB, nullable=False)
    type = Column(String(16), nullable=False)  # diary/comic
    style_key = Column(String(32), nullable=False)
    status = Column(String(16), default="pending")  # pending/processing/done/failed
    progress = Column(Integer, default=0)
    current_step = Column(String(32))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="generations")
    outputs = relationship("Output", back_populates="generation")
