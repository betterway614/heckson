from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.db_types import GUID


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    openid = Column(String(128), unique=True, nullable=False, index=True)
    unionid = Column(String(128), nullable=True)
    nickname = Column(String(64))
    avatar = Column(String(512))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memories = relationship("Memory", back_populates="user")
    generations = relationship("Generation", back_populates="user")
