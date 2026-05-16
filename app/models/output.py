from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Output(Base):
    __tablename__ = "outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id = Column(UUID(as_uuid=True), ForeignKey("generations.id"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)  # image/audio/video
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    generation = relationship("Generation", back_populates="outputs")
