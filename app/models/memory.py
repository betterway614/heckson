from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content_text = Column(Text)
    memory_date = Column(Date, nullable=False, index=True)
    mood_tag = Column(String(32))
    metadata_json = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="memories")
    media = relationship("Media", back_populates="memory")
