from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.db_types import GUID, JSONVariant


class Memory(Base):
    __tablename__ = "memories"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    content_text = Column(Text)
    memory_date = Column(Date, nullable=False)
    mood_tag = Column(String(32))
    metadata_json = Column(JSONVariant)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memories")
    media = relationship("Media", back_populates="memory")
