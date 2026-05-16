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
    status = Column(String(32), default="pending", index=True)  # pending/processing/pending_confirmation/done/failed
    progress = Column(Integer, default=0)
    current_step = Column(String(32))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)

    # 两阶段工作流字段
    stage = Column(String(32), default="vlm_parse")  # vlm_parse/confirmed/img_gen/script_gen/video_gen
    vlm_raw_metadata = Column(JSONB)                  # VLM原始解析结果
    user_edited_prompt = Column(Text)                  # 用户编辑后的提示词
    llm_polished_prompt = Column(Text)                 # LLM润色后的提示词
    final_prompt = Column(Text)                        # 最终确认的提示词
    prompt_confirmed = Column(Boolean, default=False)  # 用户是否确认

    # 视频生成相关字段
    video_params = Column(JSONB)           # 视频参数（分辨率、时长、风格、时间范围）
    video_script = Column(Text)            # LLM 生成的视频脚本
    video_url = Column(String(512))        # 生成的视频文件路径
    video_resolution = Column(String(32))  # 视频分辨率（如 "1280x720"）
    video_duration = Column(Integer)       # 视频时长（秒）
    video_style = Column(String(32))       # 视频风格

    user = relationship("User", back_populates="generations")
    outputs = relationship("Output", back_populates="generation")
