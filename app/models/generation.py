from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey
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
    status = Column(String(32), default="pending")  # pending/processing/pending_confirmation/done/failed
    progress = Column(Integer, default=0)
    current_step = Column(String(32))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # 两阶段工作流字段
    stage = Column(String(32), default="vlm_parse")  # vlm_parse/confirmed/img_gen
    vlm_raw_metadata = Column(JSONB)                  # VLM原始解析结果
    user_edited_prompt = Column(Text)                  # 用户编辑后的提示词
    llm_polished_prompt = Column(Text)                 # LLM润色后的提示词
    final_prompt = Column(Text)                        # 最终确认的提示词
    prompt_confirmed = Column(Boolean, default=False)  # 用户是否确认

    user = relationship("User", back_populates="generations")
    outputs = relationship("Output", back_populates="generation")
