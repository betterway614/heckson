from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.db_types import GUID, JSONVariant


class Output(Base):
    __tablename__ = "outputs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    generation_id = Column(GUID(), ForeignKey("generations.id"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)  # image/audio/video
    metadata_json = Column("metadata", JSONVariant)
    created_at = Column(DateTime, default=datetime.utcnow)

    generation = relationship("Generation", back_populates="outputs")
