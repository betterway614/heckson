from pydantic import BaseModel, validator
from datetime import date
from enum import Enum
from typing import Optional


class VideoStyleEnum(str, Enum):
    """视频风格枚举"""
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    WARM_MEMORY = "warm_memory"
    VIBRANT = "vibrant"


class VideoResolutionEnum(str, Enum):
    """视频分辨率枚举"""
    HD_LANDSCAPE = "1280x720"
    HD_PORTRAIT = "720x1280"
    FHD_LANDSCAPE = "1920x1080"
    FHD_PORTRAIT = "1080x1920"


# 视频风格配置
VIDEO_STYLES = {
    "cinematic": {
        "name": "电影感",
        "description": "电影级画质，戏剧性构图，专业调色",
        "prompt_prefix": "Cinematic shot, dramatic lighting, professional color grading, "
    },
    "documentary": {
        "name": "纪录片",
        "description": "真实记录风格，自然光线，纪实感",
        "prompt_prefix": "Documentary style, natural lighting, realistic, "
    },
    "warm_memory": {
        "name": "温馨回忆",
        "description": "柔和色调，温暖氛围，怀旧感",
        "prompt_prefix": "Warm tones, soft lighting, nostalgic atmosphere, "
    },
    "vibrant": {
        "name": "活力四射",
        "description": "鲜艳色彩，动态镜头，充满活力",
        "prompt_prefix": "Vibrant colors, dynamic camera movement, energetic, "
    }
}


class VideoGenerationCreate(BaseModel):
    """视频生成请求"""
    start_date: date
    end_date: date
    style: str = "cinematic"
    resolution: str = "1280x720"

    @validator("style")
    def validate_style(cls, v):
        if v not in VIDEO_STYLES:
            raise ValueError(f"Invalid style: {v}. Available: {list(VIDEO_STYLES.keys())}")
        return v

    @validator("resolution")
    def validate_resolution(cls, v):
        valid_resolutions = [e.value for e in VideoResolutionEnum]
        if v not in valid_resolutions:
            raise ValueError(f"Invalid resolution: {v}. Available: {valid_resolutions}")
        return v


class VideoScriptUpdate(BaseModel):
    """视频脚本更新"""
    script: str


class VideoGenerationResponse(BaseModel):
    """视频生成响应"""
    id: str
    type: str
    status: str
    stage: Optional[str] = None
    progress: int = 0
    video_script: Optional[str] = None
    video_url: Optional[str] = None
    video_resolution: Optional[str] = None
    video_duration: Optional[int] = None
    video_style: Optional[str] = None
    video_params: Optional[dict] = None
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True
