# 视频生成功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现基于用户记忆数据生成视频的功能，使用 wan2.7 模型

**Architecture:** 扩展现有 Generation 模型，新增 VideoGenWorkflow 两阶段工作流（脚本生成 → 视频生成），复用现有 API 路由和进度推送机制

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, 阿里云百炼 wan2.7 API, Vue.js 3

---

## 文件结构

### 新建文件
- `app/services/video_service.py` - 视频生成服务（封装 wan2.7 API）
- `app/workflows/video.py` - 视频生成工作流
- `app/schemas/video.py` - 视频相关 Schema 定义
- `tests/test_api/test_video_gen.py` - 视频生成 API 测试
- `tests/test_video_workflow.py` - 视频工作流测试

### 修改文件
- `app/models/generation.py` - 新增视频相关字段
- `app/api/generations.py` - 新增视频生成 API 端点
- `app/config.py` - 新增视频配置项
- `app/services/llm_service.py` - 新增视频脚本生成方法
- `frontend/TimeCollection/app.js` - 前端视频生成功能
- `frontend/TimeCollection/index.html` - 前端视频生成 UI

---

## Task 1: 扩展 Generation 模型

**Files:**
- Modify: `app/models/generation.py`
- Test: `tests/test_video_workflow.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py

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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_generation_has_video_fields -v
```

预期输出：FAIL - AttributeError: 'Generation' object has no attribute 'video_params'

- [ ] **Step 3: 编写最小实现**

```python
# app/models/generation.py

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
    type = Column(String(16), nullable=False)  # diary/comic/video
    style_key = Column(String(32), nullable=False)
    status = Column(String(32), default="pending")  # pending/processing/pending_confirmation/done/failed
    progress = Column(Integer, default=0)
    current_step = Column(String(32))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_generation_has_video_fields -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/models/generation.py tests/test_video_workflow.py
git commit -m "feat: add video fields to Generation model"
```

---

## Task 2: 添加视频配置项

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py (追加)

def test_settings_has_video_config():
    """测试 Settings 包含视频配置项"""
    from app.config import get_settings

    settings = get_settings()

    assert hasattr(settings, 'video_model')
    assert hasattr(settings, 'video_default_resolution')
    assert hasattr(settings, 'video_default_duration')
    assert hasattr(settings, 'video_default_style')
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_settings_has_video_config -v
```

预期输出：FAIL - AttributeError

- [ ] **Step 3: 编写最小实现**

```python
# app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://betterway:9a301301@localhost:5432/you_time"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 阿里云百炼平台
    dashscope_api_key: str = ""

    # 模型配置 - 基础模型（向后兼容）
    llm_model: str = "qwen-plus"
    vlm_model: str = "qwen-vl-plus"
    image_model: str = "wanx-v1"
    tts_model: str = "sambert-zhichu-v1"
    asr_model: str = "paraformer-v2"

    # 模型配置 - 功能细分（可选覆盖）
    # LLM模型配置
    llm_script_model: Optional[str] = None        # 文案生成
    llm_polish_model: Optional[str] = None        # 提示词润色
    llm_analysis_model: Optional[str] = None      # 内容分析
    llm_summary_model: Optional[str] = None       # 摘要生成

    # 视频生成配置
    video_model: str = "wan2.7"
    video_default_resolution: str = "1280x720"
    video_default_duration: int = 15
    video_default_style: str = "cinematic"

    # 文件存储
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_llm_model(self, task: str = "default") -> str:
        """获取LLM模型，支持按任务类型选择"""
        task_model_map = {
            "script": self.llm_script_model,
            "polish": self.llm_polish_model,
            "analysis": self.llm_analysis_model,
            "summary": self.llm_summary_model,
        }
        # 优先使用任务特定模型，否则使用基础模型
        return task_model_map.get(task) or self.llm_model


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# 可用模型配置（供参考和验证）
AVAILABLE_MODELS = {
    "llm": {
        "qwen-turbo": {"speed": "fast", "quality": "standard", "cost": "low"},
        "qwen-plus": {"speed": "medium", "quality": "high", "cost": "medium"},
        "qwen-max": {"speed": "slow", "quality": "highest", "cost": "high"},
        "qwen-max-longcontext": {"speed": "slow", "quality": "highest", "cost": "high", "context": "long"},
    },
    "vlm": {
        "qwen-vl-plus": {"speed": "medium", "quality": "high", "cost": "medium"},
        "qwen-vl-max": {"speed": "slow", "quality": "highest", "cost": "high"},
    },
    "image": {
        "wanx-v1": {"type": "standard"},
        "wanx-v2": {"type": "enhanced"},
    },
    "video": {
        "wan2.7": {"type": "standard", "duration": "15s"},
    },
    "tts": {
        "sambert-zhichu-v1": {"voice": "zhichu"},
        "sambert-zhiyuan-v1": {"voice": "zhiyuan"},
    },
    "asr": {
        "paraformer-v2": {"type": "realtime", "language": "zh-CN"},
        "paraformer-v1": {"type": "file", "language": "zh-CN"},
    }
}


def get_model_info(model_type: str, model_name: str) -> Optional[Dict]:
    """获取模型信息"""
    return AVAILABLE_MODELS.get(model_type, {}).get(model_name)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_settings_has_video_config -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/config.py
git commit -m "feat: add video generation config"
```

---

## Task 3: 创建视频 Schema 定义

**Files:**
- Create: `app/schemas/video.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py (追加)

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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_schemas_exist -v
```

预期输出：FAIL - ModuleNotFoundError: No module named 'app.schemas.video'

- [ ] **Step 3: 编写最小实现**

```python
# app/schemas/video.py

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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_schemas_exist -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/schemas/video.py tests/test_video_workflow.py
git commit -m "feat: add video generation schemas"
```

---

## Task 4: 创建视频服务

**Files:**
- Create: `app/services/video_service.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py (追加)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_video_service_generate_video():
    """测试视频服务生成视频"""
    from app.services.video_service import VideoService

    service = VideoService()

    # Mock DashScope API 调用
    with patch('app.services.video_service.VideoSynthesis') as mock_synthesis:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.results = [MagicMock(url="http://example.com/video.mp4")]
        mock_synthesis.call.return_value = mock_response

        # Mock 文件下载
        with patch('app.services.video_service.urllib.request.urlretrieve') as mock_download:
            mock_download.return_value = None

            result = await service.generate_video(
                prompt="Test prompt",
                resolution="1280x720",
                duration=15,
                generation_id="test-id"
            )

            assert result is not None
            assert "video.mp4" in result
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_service_generate_video -v
```

预期输出：FAIL - ModuleNotFoundError: No module named 'app.services.video_service'

- [ ] **Step 3: 编写最小实现**

```python
# app/services/video_service.py

import os
from pathlib import Path
from http import HTTPStatus
import urllib.request

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from dashscope import VideoSynthesis
    import dashscope
    dashscope.api_key = settings.dashscope_api_key
    USE_MOCK = False
except ImportError:
    # 创建 Mock 类
    class MockVideoSynthesis:
        @staticmethod
        def call(**kwargs):
            class MockResponse:
                status_code = 200
                class output:
                    class results:
                        @staticmethod
                        def __getitem__(index):
                            class Result:
                                url = "http://example.com/mock-video.mp4"
                            return Result()
            return MockResponse()
    VideoSynthesis = MockVideoSynthesis
    USE_MOCK = True


class VideoService:
    """视频生成服务"""

    def __init__(self):
        self.model = settings.video_model

    async def generate_video(
        self,
        prompt: str,
        resolution: str = "1280x720",
        duration: int = 15,
        generation_id: str = None
    ) -> str:
        """
        生成视频

        Args:
            prompt: 视频生成提示词
            resolution: 分辨率（如 "1280x720"）
            duration: 时长（秒）
            generation_id: 生成任务 ID

        Returns:
            str: 视频文件路径
        """
        # 调用视频生成
        response = VideoSynthesis.call(
            model=self.model,
            prompt=prompt,
            size=resolution,
            duration=duration
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"视频生成失败: {response.code} - {response.message}")

        # 获取视频URL并下载
        video_url = response.output.results[0].url

        # 保存视频
        output_path = get_output_path(generation_id, "video.mp4")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 下载视频
        urllib.request.urlretrieve(video_url, output_path)

        return output_path


# 单例
video_service = VideoService()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_service_generate_video -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/video_service.py tests/test_video_workflow.py
git commit -m "feat: add video generation service"
```

---

## Task 5: 扩展 LLM 服务 - 视频脚本生成

**Files:**
- Modify: `app/services/llm_service.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py (追化)

@pytest.mark.asyncio
async def test_llm_service_generate_video_script():
    """测试 LLM 服务生成视频脚本"""
    from app.services.llm_service import llm_service
    from app.models.memory import Memory
    from datetime import date

    # 创建测试记忆
    memories = [
        Memory(
            content_text="今天去了公园，天气很好",
            memory_date=date(2026, 5, 10)
        ),
        Memory(
            content_text="和朋友一起吃了火锅",
            memory_date=date(2026, 5, 11)
        )
    ]

    # Mock LLM 调用
    with patch.object(llm_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "在阳光明媚的日子里，主人公走进了公园..."

        script = await llm_service.generate_video_script(
            memories=memories,
            style="cinematic"
        )

        assert script is not None
        assert len(script) > 0
        mock_llm.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_llm_service_generate_video_script -v
```

预期输出：FAIL - AttributeError: 'LLMService' object has no attribute 'generate_video_script'

- [ ] **Step 3: 编写最小实现**

```python
# app/services/llm_service.py (追加方法)

class LLMService:
    # ... 现有方法 ...

    async def generate_video_script(
        self,
        memories: list,
        style: str = "cinematic"
    ) -> str:
        """
        根据记忆生成视频脚本

        Args:
            memories: 记忆列表（已按日期排序）
            style: 视频风格

        Returns:
            str: 视频脚本
        """
        # 构建记忆文本
        memory_texts = []
        for i, memory in enumerate(memories, 1):
            date_str = memory.memory_date.strftime("%Y年%m月%d日")
            text = memory.content_text or "图片记忆"
            memory_texts.append(f"{i}. [{date_str}] {text}")

        memories_str = "\n".join(memory_texts)

        prompt = f"""你是一位专业的视频脚本编剧。请根据以下记忆内容，创作一个 15 秒的视频脚本。

记忆内容（按时间顺序）：
{memories_str}

视频风格：{style}

要求：
1. 脚本应以时间顺序串联这些记忆
2. 语言生动、有画面感
3. 适合 15 秒视频的节奏
4. 包含场景描述和旁白文字

请直接输出脚本内容，不要包含其他说明。"""

        # 调用 LLM
        response = await self._call_llm(prompt)
        return response
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_llm_service_generate_video_script -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/llm_service.py tests/test_video_workflow.py
git commit -m "feat: add video script generation to LLM service"
```

---

## Task 6: 创建视频工作流

**Files:**
- Create: `app/workflows/video.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_video_workflow.py (追化)

@pytest.mark.asyncio
async def test_video_workflow_define_steps():
    """测试视频工作流定义步骤"""
    from app.workflows.video import VideoGenWorkflow
    from app.models.generation import Generation
    from unittest.mock import MagicMock

    # 创建模拟对象
    db = AsyncMock()
    generation = Generation(
        type="video",
        video_style="cinematic",
        video_resolution="1280x720",
        video_duration=15,
        video_params={
            "date_range": {
                "start": "2026-05-01",
                "end": "2026-05-16"
            }
        }
    )

    workflow = VideoGenWorkflow(db, generation)
    steps = workflow.define_steps()

    assert steps == ["script_gen", "video_gen"]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_workflow_define_steps -v
```

预期输出：FAIL - ModuleNotFoundError: No module named 'app.workflows.video'

- [ ] **Step 3: 编写最小实现**

```python
# app/workflows/video.py

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from app.models.generation import Generation
from app.models.memory import Memory
from app.workflows.base import BaseWorkflow
from app.services.llm_service import llm_service
from app.services.video_service import video_service
from app.schemas.video import VIDEO_STYLES


class VideoGenWorkflow(BaseWorkflow):
    """
    视频生成工作流（两阶段）

    阶段1：脚本生成（script_gen）
      - 读取时间范围内的记忆
      - 按 memory_date 排序
      - LLM 生成视频脚本
      - 状态变为 pending_confirmation

    阶段2：视频生成（video_gen）
      - 用户确认/编辑脚本
      - 调用 wan2.7 API
      - 下载视频文件
      - 状态变为 done
    """

    def __init__(self, db: AsyncSession, generation: Generation):
        super().__init__(db, generation)

    def define_steps(self) -> list[str]:
        return ["script_gen", "video_gen"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "script_gen":
            return await self._script_gen()
        elif step == "video_gen":
            return await self._video_gen()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _get_memories_in_range(self) -> list[Memory]:
        """获取时间范围内的记忆"""
        date_range = self.generation.video_params.get("date_range", {})
        start_date = date_range.get("start")
        end_date = date_range.get("end")

        if not start_date or not end_date:
            raise ValueError("Missing date_range in video_params")

        stmt = (
            select(Memory)
            .where(Memory.user_id == self.generation.user_id)
            .where(Memory.memory_date >= start_date)
            .where(Memory.memory_date <= end_date)
            .order_by(Memory.memory_date)
        )

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        if not memories:
            raise ValueError(f"No memories found in date range: {start_date} to {end_date}")

        return list(memories)

    async def _script_gen(self) -> dict[str, Any]:
        """阶段1：生成视频脚本"""
        # 1. 获取时间范围内的记忆
        memories = await self._get_memories_in_range()

        # 2. 调用 LLM 生成视频脚本
        script = await llm_service.generate_video_script(
            memories=memories,
            style=self.generation.video_style
        )

        # 3. 保存脚本
        self.generation.video_script = script
        await self.db.commit()

        return {"script": script, "memory_count": len(memories)}

    async def _video_gen(self) -> dict[str, Any]:
        """阶段2：生成视频"""
        # 1. 获取用户确认的脚本
        script = self.generation.video_script
        if not script:
            raise ValueError("Video script not found")

        # 2. 构建完整提示词
        style_info = VIDEO_STYLES.get(self.generation.video_style, {})
        prompt_prefix = style_info.get("prompt_prefix", "")
        full_prompt = f"{prompt_prefix}{script}"

        # 3. 调用视频生成服务
        video_url = await video_service.generate_video(
            prompt=full_prompt,
            resolution=self.generation.video_resolution,
            duration=self.generation.video_duration,
            generation_id=str(self.generation.id)
        )

        # 4. 保存视频路径
        self.generation.video_url = video_url
        await self.db.commit()

        return {"video_url": video_url}

    async def run_script_gen(self) -> dict[str, Any]:
        """运行阶段1：脚本生成"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "script_gen"
            await self.db.commit()

            # 执行脚本生成
            await self.update_progress("script_gen", 50)
            result = await self._script_gen()

            # 完成，等待用户确认
            self.generation.status = "pending_confirmation"
            self.generation.progress = 100
            self.generation.current_step = "script_gen"
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise

    async def run_video_gen(self) -> dict[str, Any]:
        """运行阶段2：视频生成"""
        try:
            self.generation.status = "processing"
            self.generation.stage = "video_gen"
            self.generation.progress = 0
            await self.db.commit()

            # 执行视频生成
            await self.update_progress("video_gen", 50)
            result = await self._video_gen()

            # 完成
            self.generation.status = "done"
            self.generation.progress = 100
            self.generation.current_step = "done"
            from datetime import datetime
            self.generation.completed_at = datetime.utcnow()
            await self.db.commit()

            return result

        except Exception as e:
            self.generation.status = "failed"
            self.generation.error_message = str(e)
            await self.db.commit()
            raise
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_workflow.py::test_video_workflow_define_steps -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/workflows/video.py tests/test_video_workflow.py
git commit -m "feat: add video generation workflow"
```

---

## Task 7: 添加视频生成 API 端点

**Files:**
- Modify: `app/api/generations.py`

- [ ] **Step 1: 编写失败的测试**

```python
# tests/test_api/test_video_gen.py

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_video_generation():
    """测试创建视频生成任务"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/generations/video",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-16",
                "style": "cinematic",
                "resolution": "1280x720"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "video"
        assert data["status"] == "processing"
        assert data["video_style"] == "cinematic"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_api/test_video_gen.py::test_create_video_generation -v
```

预期输出：FAIL - 404 Not Found

- [ ] **Step 3: 编写最小实现**

```python
# app/api/generations.py (追加路由)

from app.schemas.video import (
    VideoGenerationCreate,
    VideoScriptUpdate,
    VIDEO_STYLES
)
from app.workflows.video import VideoGenWorkflow


@router.post("/video", response_model=GenerationResponse)
async def create_video_generation(
    video_data: VideoGenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建视频生成任务

    参数：
    - start_date: 开始日期
    - end_date: 结束日期
    - style: 视频风格（cinematic/documentary/warm_memory/vibrant）
    - resolution: 视频分辨率（1280x720/720x1280/1920x1080/1080x1920）
    """
    user_id = "00000000-0000-0000-0000-000000000001"

    # 创建 Generation 记录
    generation = Generation(
        user_id=user_id,
        memory_ids=[],  # 视频生成不依赖特定记忆ID
        type="video",
        style_key=video_data.style,
        video_params={
            "resolution": video_data.resolution,
            "duration": 15,
            "style": video_data.style,
            "date_range": {
                "start": video_data.start_date.isoformat(),
                "end": video_data.end_date.isoformat()
            }
        },
        video_resolution=video_data.resolution,
        video_duration=15,
        video_style=video_data.style,
        status="processing",
        stage="script_gen"
    )
    db.add(generation)
    await db.commit()
    await db.refresh(generation)

    # 异步启动阶段1：脚本生成
    asyncio.create_task(_run_video_script_workflow(db, generation))

    return generation


@router.get("/{generation_id}/video-script")
async def get_video_script(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取视频脚本"""
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.type != "video":
        raise HTTPException(status_code=400, detail="Generation is not a video type")

    return {
        "generation_id": str(generation.id),
        "script": generation.video_script,
        "status": generation.status
    }


@router.put("/{generation_id}/video-script", response_model=GenerationResponse)
async def update_video_script(
    generation_id: UUID,
    script_data: VideoScriptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新视频脚本（用户编辑）"""
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for script editing")

    generation.video_script = script_data.script
    await db.commit()
    await db.refresh(generation)

    return generation


@router.post("/{generation_id}/confirm-video", response_model=GenerationResponse)
async def confirm_video_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    确认视频脚本，触发阶段2：视频生成

    用户确认脚本后，调用 wan2.7 生成视频
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    result = await db.execute(stmt)
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for confirmation")

    # 更新状态
    generation.status = "processing"
    generation.stage = "video_gen"
    await db.commit()

    # 异步启动阶段2：视频生成
    asyncio.create_task(_run_video_gen_workflow(db, generation))

    await db.refresh(generation)
    return generation


@router.get("/video-styles")
async def list_video_styles():
    """获取所有视频风格列表"""
    return VIDEO_STYLES


async def _run_video_script_workflow(db: AsyncSession, generation: Generation):
    """运行阶段1：脚本生成"""
    try:
        workflow = VideoGenWorkflow(db, generation)
        await workflow.run_script_gen()
    except Exception as e:
        print(f"Video script workflow failed: {e}")


async def _run_video_gen_workflow(db: AsyncSession, generation: Generation):
    """运行阶段2：视频生成"""
    try:
        workflow = VideoGenWorkflow(db, generation)
        await workflow.run_video_gen()
    except Exception as e:
        print(f"Video generation workflow failed: {e}")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_api/test_video_gen.py::test_create_video_generation -v
```

预期输出：PASS

- [ ] **Step 5: 提交**

```bash
git add app/api/generations.py tests/test_api/test_video_gen.py
git commit -m "feat: add video generation API endpoints"
```

---

## Task 8: 前端 - 视频生成入口

**Files:**
- Modify: `frontend/TimeCollection/index.html`
- Modify: `frontend/TimeCollection/app.js`
- Modify: `frontend/TimeCollection/api.js`

- [ ] **Step 1: 在 api.js 添加视频 API 调用**

```javascript
// frontend/TimeCollection/api.js (追加)

// 视频生成相关 API
async function createVideoGeneration(data) {
    const response = await fetch(`${API_BASE_URL}/api/generations/video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response.json();
}

async function getVideoScript(generationId) {
    const response = await fetch(`${API_BASE_URL}/api/generations/${generationId}/video-script`);
    return response.json();
}

async function updateVideoScript(generationId, script) {
    const response = await fetch(`${API_BASE_URL}/api/generations/${generationId}/video-script`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script })
    });
    return response.json();
}

async function confirmVideoGeneration(generationId) {
    const response = await fetch(`${API_BASE_URL}/api/generations/${generationId}/confirm-video`, {
        method: 'POST'
    });
    return response.json();
}

async function listVideoStyles() {
    const response = await fetch(`${API_BASE_URL}/api/generations/video-styles`);
    return response.json();
}
```

- [ ] **Step 2: 在 app.js 添加视频生成状态和方法**

```javascript
// frontend/TimeCollection/app.js (追加)

// 视频生成状态
const showVideoGenModal = ref(false);
const videoStartDate = ref('');
const videoEndDate = ref('');
const videoStyle = ref('cinematic');
const videoResolution = ref('1280x720');
const videoStyles = ref({});
const generatingVideo = ref(false);
const videoProgress = ref(0);
const currentVideoGeneration = ref(null);
const videoScript = ref('');
const showScriptPreview = ref(false);
const showVideoPlayer = ref(false);
const videoUrl = ref('');

// 预设时间范围
const presetRanges = [
    { label: '最近7天', days: 7 },
    { label: '最近30天', days: 30 },
    { label: '最近90天', days: 90 }
];

// 分辨率选项
const resolutionOptions = [
    { value: '1280x720', label: '720p 横屏' },
    { value: '720x1280', label: '720p 竖屏' },
    { value: '1920x1080', label: '1080p 横屏' },
    { value: '1080x1920', label: '1080p 竖屏' }
];

// 选择预设时间范围
function selectPresetRange(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    videoStartDate.value = start.toISOString().split('T')[0];
    videoEndDate.value = end.toISOString().split('T')[0];
}

// 加载视频风格
async function loadVideoStyles() {
    try {
        videoStyles.value = await listVideoStyles();
    } catch (error) {
        console.error('加载视频风格失败:', error);
    }
}

// 生成视频
async function generateVideo() {
    if (!videoStartDate.value || !videoEndDate.value) {
        alert('请选择时间范围');
        return;
    }

    try {
        generatingVideo.value = true;
        videoProgress.value = 0;

        // 1. 创建视频生成任务
        const generation = await createVideoGeneration({
            start_date: videoStartDate.value,
            end_date: videoEndDate.value,
            style: videoStyle.value,
            resolution: videoResolution.value
        });

        currentVideoGeneration.value = generation;

        // 2. 监听进度
        streamGenerationProgress(generation.id, {
            onProgress: (data) => {
                videoProgress.value = data.progress || 0;
            },
            onComplete: (data) => {
                generatingVideo.value = false;

                if (data.status === 'pending_confirmation') {
                    // 脚本生成完成，显示脚本预览
                    videoScript.value = data.video_script || '';
                    showVideoGenModal.value = false;
                    showScriptPreview.value = true;
                } else if (data.status === 'done') {
                    // 视频生成完成，显示视频播放器
                    videoUrl.value = data.video_url;
                    showScriptPreview.value = false;
                    showVideoPlayer.value = true;
                }
            },
            onError: (error) => {
                generatingVideo.value = false;
                console.error('视频生成失败:', error);
                alert('视频生成失败，请重试');
            }
        });

    } catch (error) {
        generatingVideo.value = false;
        console.error('创建视频生成任务失败:', error);
        alert('创建失败，请重试');
    }
}

// 确认脚本，生成视频
async function confirmScript() {
    if (!currentVideoGeneration.value) return;

    try {
        generatingVideo.value = true;
        videoProgress.value = 0;

        // 更新脚本（如果用户编辑了）
        await updateVideoScript(currentVideoGeneration.value.id, videoScript.value);

        // 确认生成视频
        await confirmVideoGeneration(currentVideoGeneration.value.id);

        // 监听进度
        streamGenerationProgress(currentVideoGeneration.value.id, {
            onProgress: (data) => {
                videoProgress.value = data.progress || 0;
            },
            onComplete: (data) => {
                generatingVideo.value = false;

                if (data.status === 'done') {
                    videoUrl.value = data.video_url;
                    showScriptPreview.value = false;
                    showVideoPlayer.value = true;
                }
            },
            onError: (error) => {
                generatingVideo.value = false;
                console.error('视频生成失败:', error);
                alert('视频生成失败，请重试');
            }
        });

    } catch (error) {
        generatingVideo.value = false;
        console.error('确认脚本失败:', error);
        alert('确认失败，请重试');
    }
}

// 初始化
onMounted(() => {
    // ... 现有初始化 ...
    loadVideoStyles();
});

// 返回状态和方法
return {
    // ... 现有返回值 ...
    showVideoGenModal,
    videoStartDate,
    videoEndDate,
    videoStyle,
    videoResolution,
    videoStyles,
    generatingVideo,
    videoProgress,
    currentVideoGeneration,
    videoScript,
    showScriptPreview,
    showVideoPlayer,
    videoUrl,
    presetRanges,
    resolutionOptions,
    selectPresetRange,
    generateVideo,
    confirmScript
};
```

- [ ] **Step 3: 在 index.html 添加视频生成 UI**

```html
<!-- index.html - 在故事集页面追加 -->

<!-- 视频生成入口按钮 -->
<div class="video-gen-section" style="margin: 20px; text-align: center;">
    <button class="btn btn-primary btn-lg" @click="showVideoGenModal = true">
        <i class="fas fa-video"></i> 生成视频回忆
    </button>
</div>

<!-- 视频生成弹窗 -->
<div class="modal-overlay" v-show="showVideoGenModal" @click.self="showVideoGenModal = false">
    <div class="modal-content" style="max-width: 500px;">
        <div class="modal-header">
            <span>生成视频回忆</span>
            <button class="close-modal" @click="showVideoGenModal = false">&times;</button>
        </div>
        <div class="modal-body" style="padding: 20px;">
            <!-- 时间范围选择 -->
            <div class="mb-3">
                <label class="form-label">选择时间范围</label>
                <div class="d-flex gap-2 mb-2">
                    <button v-for="range in presetRanges" :key="range.days"
                            class="btn btn-outline-secondary btn-sm"
                            @click="selectPresetRange(range.days)">
                        {{ range.label }}
                    </button>
                </div>
                <div class="d-flex gap-2">
                    <input type="date" class="form-control" v-model="videoStartDate">
                    <span class="align-self-center">至</span>
                    <input type="date" class="form-control" v-model="videoEndDate">
                </div>
            </div>

            <!-- 风格选择 -->
            <div class="mb-3">
                <label class="form-label">选择视频风格</label>
                <div class="d-flex flex-wrap gap-2">
                    <button v-for="(style, key) in videoStyles" :key="key"
                            :class="['btn', videoStyle === key ? 'btn-primary' : 'btn-outline-primary']"
                            @click="videoStyle = key">
                        {{ style.name }}
                    </button>
                </div>
                <small class="text-muted">{{ videoStyles[videoStyle]?.description }}</small>
            </div>

            <!-- 分辨率选择 -->
            <div class="mb-3">
                <label class="form-label">选择分辨率</label>
                <select class="form-select" v-model="videoResolution">
                    <option v-for="opt in resolutionOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                    </option>
                </select>
            </div>

            <!-- 生成进度 -->
            <div v-if="generatingVideo" class="mt-3">
                <div class="progress">
                    <div class="progress-bar" :style="{ width: videoProgress + '%' }">
                        {{ videoProgress }}%
                    </div>
                </div>
                <small class="text-muted">正在生成中，请稍候...</small>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" @click="showVideoGenModal = false">取消</button>
            <button class="btn btn-primary" @click="generateVideo" :disabled="generatingVideo">
                {{ generatingVideo ? '生成中...' : '开始生成' }}
            </button>
        </div>
    </div>
</div>

<!-- 脚本预览弹窗 -->
<div class="modal-overlay" v-show="showScriptPreview" @click.self="showScriptPreview = false">
    <div class="modal-content" style="max-width: 600px;">
        <div class="modal-header">
            <span>视频脚本预览</span>
            <button class="close-modal" @click="showScriptPreview = false">&times;</button>
        </div>
        <div class="modal-body" style="padding: 20px;">
            <div class="mb-3">
                <label class="form-label">AI 生成的视频脚本（可编辑）</label>
                <textarea class="form-control" v-model="videoScript" rows="10"
                          placeholder="视频脚本将在这里显示..."></textarea>
            </div>

            <!-- 生成进度 -->
            <div v-if="generatingVideo" class="mt-3">
                <div class="progress">
                    <div class="progress-bar" :style="{ width: videoProgress + '%' }">
                        {{ videoProgress }}%
                    </div>
                </div>
                <small class="text-muted">正在生成视频，请稍候...</small>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" @click="showScriptPreview = false">取消</button>
            <button class="btn btn-primary" @click="confirmScript" :disabled="generatingVideo">
                {{ generatingVideo ? '生成中...' : '确认生成视频' }}
            </button>
        </div>
    </div>
</div>

<!-- 视频播放器弹窗 -->
<div class="modal-overlay" v-show="showVideoPlayer" @click.self="showVideoPlayer = false">
    <div class="modal-content" style="max-width: 800px;">
        <div class="modal-header">
            <span>视频预览</span>
            <button class="close-modal" @click="showVideoPlayer = false">&times;</button>
        </div>
        <div class="modal-body" style="padding: 20px;">
            <video controls style="width: 100%;">
                <source :src="videoUrl" type="video/mp4">
                您的浏览器不支持视频播放
            </video>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" @click="showVideoPlayer = false">关闭</button>
            <a :href="videoUrl" download class="btn btn-primary">
                <i class="fas fa-download"></i> 下载视频
            </a>
        </div>
    </div>
</div>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/TimeCollection/api.js frontend/TimeCollection/app.js frontend/TimeCollection/index.html
git commit -m "feat: add video generation frontend UI"
```

---

## Task 9: 集成测试

**Files:**
- Create: `tests/test_video_gen_smoke.py`

- [ ] **Step 1: 编写完整的烟雾测试**

```python
# tests/test_video_gen_smoke.py

import pytest
import asyncio
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_video_generation_smoke():
    """视频生成完整流程烟雾测试"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 获取视频风格列表
        styles_response = await client.get("/api/generations/video-styles")
        assert styles_response.status_code == 200
        styles = styles_response.json()
        assert "cinematic" in styles

        # 2. 创建视频生成任务
        create_response = await client.post(
            "/api/generations/video",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-16",
                "style": "cinematic",
                "resolution": "1280x720"
            }
        )
        assert create_response.status_code == 200
        generation = create_response.json()
        generation_id = generation["id"]
        assert generation["type"] == "video"
        assert generation["status"] == "processing"

        # 3. 等待脚本生成（轮询状态）
        for _ in range(30):  # 最多等待30秒
            status_response = await client.get(f"/api/generations/{generation_id}")
            status = status_response.json()

            if status["status"] == "pending_confirmation":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Generation failed: {status.get('error_message')}")

            await asyncio.sleep(1)

        # 4. 获取视频脚本
        script_response = await client.get(f"/api/generations/{generation_id}/video-script")
        assert script_response.status_code == 200
        script_data = script_response.json()
        assert script_data["script"] is not None

        # 5. 确认脚本，生成视频
        confirm_response = await client.post(f"/api/generations/{generation_id}/confirm-video")
        assert confirm_response.status_code == 200

        # 6. 等待视频生成
        for _ in range(60):  # 最多等待60秒
            status_response = await client.get(f"/api/generations/{generation_id}")
            status = status_response.json()

            if status["status"] == "done":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Video generation failed: {status.get('error_message')}")

            await asyncio.sleep(1)

        # 7. 验证视频生成完成
        final_status = await client.get(f"/api/generations/{generation_id}")
        final_data = final_status.json()
        assert final_data["status"] == "done"
        assert final_data["video_url"] is not None
```

- [ ] **Step 2: 运行烟雾测试**

```bash
cd e:/githubproject/heckson
python -m pytest tests/test_video_gen_smoke.py -v
```

预期输出：PASS（或在没有真实 API 的情况下跳过）

- [ ] **Step 3: 提交**

```bash
git add tests/test_video_gen_smoke.py
git commit -m "test: add video generation smoke test"
```

---

## Task 10: 文档更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md**

```markdown
# README.md (追加功能特性)

## 功能特性

- **记忆管理** - 创建、存储和检索个人记忆
- **AI 图像生成** - 根据记忆描述生成精美图片
- **AI 视频生成** - 根据记忆内容生成 15 秒视频回忆录
- **语音合成 (TTS)** - 将文字转换为语音
- **语音识别 (ASR)** - 将语音转换为文字
- **视觉语言模型 (VLM)** - 从图片中提取信息
- **日记工作流** - 自动生成日记内容

## 视频生成功能

### 功能说明
- 支持按时间范围选择记忆（最近7天/30天/90天/自定义）
- LLM 自动生成视频脚本，支持用户编辑确认
- 调用 wan2.7 模型生成 15 秒视频
- 支持多种预设风格：电影感、纪录片、温馨回忆、活力四射
- 支持多种分辨率：720p/1080p，横屏/竖屏

### API 端点
- `POST /api/generations/video` - 创建视频生成任务
- `GET /api/generations/{id}/video-script` - 获取视频脚本
- `PUT /api/generations/{id}/video-script` - 更新视频脚本
- `POST /api/generations/{id}/confirm-video` - 确认脚本，生成视频
- `GET /api/generations/video-styles` - 获取视频风格列表
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add video generation feature documentation"
```

---

## 执行顺序

建议按以下顺序执行任务：

1. Task 1: 扩展 Generation 模型
2. Task 2: 添加视频配置项
3. Task 3: 创建视频 Schema 定义
4. Task 4: 创建视频服务
5. Task 5: 扩展 LLM 服务
6. Task 6: 创建视频工作流
7. Task 7: 添加视频生成 API 端点
8. Task 8: 前端 - 视频生成入口
9. Task 9: 集成测试
10. Task 10: 文档更新

每个任务完成后运行测试验证，确保功能正常后再进行下一个任务。
