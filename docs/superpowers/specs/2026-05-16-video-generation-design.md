# 视频生成功能设计文档

## 1. 概述

### 1.1 功能目标
基于用户已有的记忆数据（文字内容和日期），自动生成视频脚本，并调用 wan2.7 模型生成 15 秒视频。

### 1.2 核心价值
- 将用户的文字记忆转化为动态视频回忆录
- 按时间顺序串联记忆，形成故事线
- 支持多种预设风格（电影感、纪录片、温馨回忆等）

### 1.3 技术栈
- **后端**：FastAPI + SQLAlchemy 2.0 (async)
- **数据库**：PostgreSQL
- **AI 模型**：阿里云百炼平台 wan2.7 视频生成模型
- **前端**：Vue.js 3 + Bootstrap 5

---

## 2. 数据模型设计

### 2.1 Generation 模型扩展

在现有 `Generation` 模型基础上新增以下字段：

```python
# app/models/generation.py

class Generation(Base):
    # ... 现有字段 ...

    # 视频生成相关字段
    video_params = Column(JSONB)           # 视频参数（分辨率、时长、风格、时间范围）
    video_script = Column(Text)            # LLM 生成的视频脚本
    video_url = Column(String(512))        # 生成的视频文件路径
    video_resolution = Column(String(32))  # 视频分辨率（如 "1280x720"）
    video_duration = Column(Integer)       # 视频时长（秒）
    video_style = Column(String(32))       # 视频风格
```

### 2.2 video_params 结构定义

```json
{
  "resolution": "1280x720",
  "duration": 15,
  "style": "cinematic",
  "date_range": {
    "start": "2026-05-01",
    "end": "2026-05-16"
  },
  "memory_count": 10
}
```

### 2.3 视频风格枚举

```python
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
```

---

## 3. 工作流设计

### 3.1 VideoGenWorkflow 类

```python
# app/workflows/video.py

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

    def define_steps(self) -> list[str]:
        return ["script_gen", "video_gen"]

    async def execute_step(self, step: str) -> dict[str, Any]:
        if step == "script_gen":
            return await self._script_gen()
        elif step == "video_gen":
            return await self._video_gen()
        else:
            raise ValueError(f"Unknown step: {step}")

    async def _script_gen(self) -> dict[str, Any]:
        """阶段1：生成视频脚本"""
        # 1. 获取时间范围内的记忆
        memories = await self._get_memories_in_range()

        # 2. 按日期排序
        memories.sort(key=lambda m: m.memory_date)

        # 3. 调用 LLM 生成视频脚本
        script = await llm_service.generate_video_script(
            memories=memories,
            style=self.generation.video_style
        )

        # 4. 保存脚本
        self.generation.video_script = script
        await self.db.commit()

        return {"script": script, "memory_count": len(memories)}

    async def _video_gen(self) -> dict[str, Any]:
        """阶段2：生成视频"""
        # 1. 获取用户确认的脚本
        script = self.generation.video_script

        # 2. 构建完整提示词
        style_info = VIDEO_STYLES[self.generation.video_style]
        full_prompt = f"{style_info['prompt_prefix']}{script}"

        # 3. 调用 wan2.7 API
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
```

### 3.2 工作流状态流转

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────┐
│  processing │ ──► │ pending_confirmation │ ──► │    done     │
│  (阶段1)    │     │  (等待用户确认)      │     │  (阶段2完成) │
└─────────────┘     └─────────────────────┘     └─────────────┘
       │                                              │
       ▼                                              ▼
   ┌───────┐                                      ┌───────┐
   │ failed │                                      │ failed │
   └───────┘                                      └───────┘
```

---

## 4. 服务层设计

### 4.1 VideoService

```python
# app/services/video_service.py

class VideoService:
    """视频生成服务"""

    def __init__(self):
        self.model = "wan2.7"  # wan2.7 模型

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
        # 调用阿里云百炼 API
        response = await self._call_dashscope_api(
            prompt=prompt,
            resolution=resolution,
            duration=duration
        )

        # 下载视频
        video_url = response.output.video_url
        output_path = get_output_path(generation_id, "video.mp4")
        await self._download_video(video_url, output_path)

        return output_path

    async def _call_dashscope_api(self, prompt, resolution, duration):
        """调用阿里云百炼 API"""
        # 使用 dashscope SDK 调用 wan2.7
        from dashscope import VideoSynthesis

        response = VideoSynthesis.call(
            model="wan2.7",
            prompt=prompt,
            size=resolution,
            duration=duration
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"视频生成失败: {response.code} - {response.message}")

        return response
```

### 4.2 LLMService 扩展

```python
# app/services/llm_service.py

class LLMService:
    # ... 现有方法 ...

    async def generate_video_script(
        self,
        memories: list[Memory],
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
        # 构建提示词
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

---

## 5. API 设计

### 5.1 新增端点

```python
# app/api/generations.py

@router.post("/video", response_model=GenerationResponse)
async def create_video_generation(
    video_data: VideoGenerationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建视频生成任务

    参数：
    - date_range: 时间范围（start_date, end_date）
    - style: 视频风格
    - resolution: 视频分辨率
    """
    # 1. 创建 Generation 记录
    generation = Generation(
        user_id=user_id,
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

    # 2. 异步启动阶段1：脚本生成
    asyncio.create_task(_run_video_workflow(db, generation))

    return generation


@router.get("/{generation_id}/video-script")
async def get_video_script(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取视频脚本"""
    generation = await _get_generation(generation_id, db)
    return {"script": generation.video_script}


@router.put("/{generation_id}/video-script")
async def update_video_script(
    generation_id: UUID,
    script_data: VideoScriptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新视频脚本（用户编辑）"""
    generation = await _get_generation(generation_id, db)

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for script editing")

    generation.video_script = script_data.script
    await db.commit()

    return generation


@router.post("/{generation_id}/confirm-video")
async def confirm_video_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    确认视频脚本，触发阶段2：视频生成

    用户确认脚本后，调用 wan2.7 生成视频
    """
    generation = await _get_generation(generation_id, db)

    if generation.status != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Generation not ready for confirmation")

    # 更新状态
    generation.status = "processing"
    generation.stage = "video_gen"
    await db.commit()

    # 异步启动阶段2：视频生成
    asyncio.create_task(_run_video_workflow(db, generation))

    return generation
```

### 5.2 Schemas 定义

```python
# app/schemas/generation.py

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
        valid_resolutions = ["1280x720", "720x1280", "1920x1080", "1080x1920"]
        if v not in valid_resolutions:
            raise ValueError(f"Invalid resolution: {v}. Available: {valid_resolutions}")
        return v


class VideoScriptUpdate(BaseModel):
    """视频脚本更新"""
    script: str
```

---

## 6. 前端设计

### 6.1 页面结构

在"故事集"页面（`stories`）新增视频生成功能入口：

```html
<!-- 视频生成入口 -->
<div class="video-gen-section">
    <button class="video-gen-btn" @click="showVideoGenModal = true">
        <i class="fas fa-video"></i>
        <span>生成视频回忆</span>
    </button>
</div>

<!-- 视频生成弹窗 -->
<div class="video-gen-modal" v-show="showVideoGenModal">
    <!-- 时间范围选择 -->
    <div class="date-range-section">
        <h3>选择时间范围</h3>
        <div class="preset-ranges">
            <button @click="selectDateRange(7)">最近7天</button>
            <button @click="selectDateRange(30)">最近30天</button>
            <button @click="selectDateRange(90)">最近90天</button>
        </div>
        <div class="custom-range">
            <input type="date" v-model="startDate">
            <input type="date" v-model="endDate">
        </div>
    </div>

    <!-- 风格选择 -->
    <div class="style-section">
        <h3>选择视频风格</h3>
        <div class="style-options">
            <div v-for="style in videoStyles" :key="style.key"
                 :class="['style-option', { active: selectedStyle === style.key }]">
                <span class="style-name">{{ style.name }}</span>
                <span class="style-desc">{{ style.description }}</span>
            </div>
        </div>
    </div>

    <!-- 分辨率选择 -->
    <div class="resolution-section">
        <h3>选择分辨率</h3>
        <div class="resolution-options">
            <button @click="resolution = '1280x720'">720p 横屏</button>
            <button @click="resolution = '720x1280'">720p 竖屏</button>
            <button @click="resolution = '1920x1080'">1080p 横屏</button>
        </div>
    </div>

    <!-- 生成按钮 -->
    <button class="generate-btn" @click="generateVideo">
        生成视频
    </button>
</div>
```

### 6.2 脚本预览和编辑界面

```html
<!-- 脚本预览弹窗 -->
<div class="script-preview-modal" v-show="showScriptPreview">
    <div class="script-content">
        <h3>视频脚本预览</h3>
        <textarea v-model="videoScript" rows="10"></textarea>
    </div>
    <div class="script-actions">
        <button @click="editScript">编辑脚本</button>
        <button @click="confirmScript">确认生成视频</button>
    </div>
</div>
```

### 6.3 视频播放器

```html
<!-- 视频播放器 -->
<div class="video-player" v-if="videoUrl">
    <video controls>
        <source :src="videoUrl" type="video/mp4">
    </video>
</div>
```

---

## 7. 文件存储结构

```
outputs/
└── {generation_id}/
    ├── video.mp4          # 生成的视频文件
    └── metadata.json      # 元数据（可选）
```

---

## 8. 配置项

### 8.1 环境变量

```bash
# .env

# 视频生成模型
VIDEO_MODEL=wan2.7

# 视频默认参数
VIDEO_DEFAULT_RESOLUTION=1280x720
VIDEO_DEFAULT_DURATION=15
VIDEO_DEFAULT_STYLE=cinematic
```

### 8.2 Settings 扩展

```python
# app/config.py

class Settings(BaseSettings):
    # ... 现有配置 ...

    # 视频生成配置
    video_model: str = "wan2.7"
    video_default_resolution: str = "1280x720"
    video_default_duration: int = 15
    video_default_style: str = "cinematic"
```

---

## 9. 测试计划

### 9.1 单元测试

- VideoService.generate_video()
- LLMService.generate_video_script()
- VideoGenWorkflow 各步骤

### 9.2 集成测试

- 完整视频生成流程
- API 端点测试
- 前后端联调

### 9.3 烟雾测试

```python
# tests/test_video_gen_smoke.py

async def test_video_generation_flow():
    """测试完整视频生成流程"""
    # 1. 创建记忆
    # 2. 创建视频生成任务
    # 3. 等待脚本生成
    # 4. 确认脚本
    # 5. 等待视频生成
    # 6. 验证视频文件存在
```

---

## 10. 风险和注意事项

### 10.1 技术风险

1. **wan2.7 API 稳定性**：需要做好错误处理和重试机制
2. **视频生成时间**：可能较长，需要异步处理和进度推送
3. **文件大小**：视频文件可能较大，需要考虑存储空间

### 10.2 用户体验

1. **进度反馈**：实时推送生成进度
2. **错误处理**：友好的错误提示
3. **预估时间**：告知用户预计等待时间

---

## 11. 后续扩展

1. **视频模板**：支持更多视频模板和转场效果
2. **背景音乐**：支持用户上传或自动生成背景音乐
3. **字幕**：自动生成字幕
4. **批量生成**：支持批量生成多个视频
5. **分享功能**：一键分享到社交媒体
