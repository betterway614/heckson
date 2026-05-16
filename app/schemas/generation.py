from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class GenerationCreate(BaseModel):
    memory_ids: List[UUID]
    type: str = "diary"
    style_key: str


class GenerationResponse(BaseModel):
    id: UUID
    user_id: UUID
    memory_ids: List[UUID]
    type: str
    style_key: str
    status: str
    progress: int
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    # 两阶段工作流字段
    stage: Optional[str] = None
    vlm_raw_metadata: Optional[Any] = None
    user_edited_prompt: Optional[str] = None
    llm_polished_prompt: Optional[str] = None
    final_prompt: Optional[str] = None
    prompt_confirmed: bool = False

    class Config:
        from_attributes = True


class GenerationProgress(BaseModel):
    generation_id: UUID
    status: str
    progress: int
    current_step: Optional[str] = None


class PromptUpdate(BaseModel):
    """用户编辑提示词"""
    user_edited_prompt: str


class PromptPolish(BaseModel):
    """LLM润色请求"""
    prompt: str


class PromptConfirm(BaseModel):
    """用户确认提示词"""
    final_prompt: str


class DiaryPolish(BaseModel):
    """日记润色请求"""
    diary_text: str
    style_key: str  # polished/douyin/xiaohongshu/moments


class DiaryPolishResponse(BaseModel):
    """日记润色响应"""
    original_text: str
    polished_text: str
    style_key: str
    style_name: str


class EmotionExtract(BaseModel):
    """情绪提取请求"""
    diary_text: str


class ComicPromptGenerate(BaseModel):
    """漫画分镜生成请求"""
    diary_text: str
    style_key: str  # comic_shuangwen/comic_zhiyu


class ComicPromptResponse(BaseModel):
    """漫画分镜响应"""
    diary_text: str
    comic_prompt: str
    style_key: str
    style_name: str


class TextPolishRequest(BaseModel):
    """独立文本润色请求（不依赖generation）"""
    text: str
    style_key: str = "polished"  # polished/moments/xiaohongshu


class TextPolishResponse(BaseModel):
    """独立文本润色响应"""
    original_text: str
    polished_text: str
    style_key: str


class DailyDiaryCreate(BaseModel):
    """一日漫画生成请求"""
    memory_date: str  # YYYY-MM-DD 格式
