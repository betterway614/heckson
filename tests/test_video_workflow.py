import pytest
from app.models.generation import Generation


def test_generation_has_video_fields():
    """测试 Generation 模型包含视频相关字段"""
    generation = Generation()

    # 验证视频字段存在
    assert hasattr(generation, 'video_params')
    assert hasattr(generation, 'video_script')
    assert hasattr(generation, 'video_url')
    assert hasattr(generation, 'video_resolution')
    assert hasattr(generation, 'video_duration')
    assert hasattr(generation, 'video_style')


def test_settings_has_video_config():
    """测试 Settings 包含视频配置项"""
    from app.config import get_settings

    settings = get_settings()

    assert hasattr(settings, 'video_model')
    assert hasattr(settings, 'video_default_resolution')
    assert hasattr(settings, 'video_default_duration')
    assert hasattr(settings, 'video_default_style')


def test_video_schemas_exist():
    """测试视频 Schema 存在"""
    from app.schemas.video import (
        VideoGenerationCreate,
        VideoScriptUpdate,
        VideoStyleEnum,
        VideoResolutionEnum
    )

    # 验证 Schema 可以实例化
    request = VideoGenerationCreate(
        start_date="2026-05-01",
        end_date="2026-05-16",
        style="cinematic",
        resolution="1280x720"
    )

    assert request.style == "cinematic"
    assert request.resolution == "1280x720"
