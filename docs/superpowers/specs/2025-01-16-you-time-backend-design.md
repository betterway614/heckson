# YOU TIME 后端架构设计文档

## 1. 项目概述

YOU TIME 是一款面向Z世代与千禧一代的"AI人生放映厅"应用。用户上传日常照片、日记文字或语音，系统自动识别元数据，生成漫画/插画风格的日记，并支持"爽文剧场"模式。

### 1.1 MVP范围

- **核心功能**：日记生成工作流
- **输出格式**：单图漫画 + 文字气泡
- **用户认证**：跳过认证，使用测试用户
- **存储**：本地文件存储

### 1.2 技术栈

| 组件 | 技术选择 |
|------|----------|
| Web框架 | FastAPI |
| 数据库 | PostgreSQL |
| 缓存/队列 | Redis |
| AI SDK | Ark SDK (LLM/VLM/图生成) + MaaS SDK (TTS) |
| 对象存储 | 本地文件系统 |
| 异步任务 | 原生Python状态机 |

---

## 2. 数据模型设计

### 2.1 User表

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    openid VARCHAR(128) UNIQUE NOT NULL,  -- 抖音小程序openid
    unionid VARCHAR(128),                 -- 跨应用统一ID（可选）
    nickname VARCHAR(64),
    avatar VARCHAR(512),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.2 Memory表（一条记忆）

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    content_text TEXT,                    -- 文字内容
    memory_date DATE NOT NULL,           -- 记忆日期（前端传入）
    mood_tag VARCHAR(32),                -- 情绪标签
    metadata_json JSONB,                 -- VLM解析结果（场景、物品等）
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.3 Media表（媒体文件）

```sql
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES memories(id),
    file_path VARCHAR(512) NOT NULL,     -- 文件路径
    file_type VARCHAR(16) NOT NULL,      -- image/audio
    original_filename VARCHAR(256),      -- 原始文件名
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.4 Generation表（生成任务）

```sql
CREATE TABLE generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    memory_ids JSONB NOT NULL,           -- 关联的记忆ID数组
    type VARCHAR(16) NOT NULL,           -- diary/comic
    style_key VARCHAR(32) NOT NULL,      -- 风格模板key
    status VARCHAR(16) DEFAULT 'pending', -- pending/processing/done/failed
    progress INTEGER DEFAULT 0,          -- 进度0-100
    current_step VARCHAR(32),            -- 当前工作流步骤
    error_message TEXT,                  -- 错误信息
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### 2.5 Output表（生成产物）

```sql
CREATE TABLE outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES generations(id),
    file_path VARCHAR(512) NOT NULL,     -- 文件路径
    file_type VARCHAR(16) NOT NULL,      -- image/audio/video
    metadata JSONB,                      -- 分辨率、时长等
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. API设计

### 3.1 记忆相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/memories | 创建记忆（上传文字+日期+情绪） |
| GET | /api/memories | 获取记忆列表 |
| GET | /api/memories/{id} | 获取记忆详情 |

### 3.2 媒体相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/media/upload | 上传媒体文件 |
| GET | /api/media/{id} | 获取媒体信息 |

### 3.3 生成相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/generations | 创建生成任务 |
| GET | /api/generations/{id} | 获取任务状态 |
| GET | /api/generations/{id}/stream | SSE推送进度 |
| GET | /api/outputs/{id} | 下载生成结果 |

### 3.4 模板相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/templates/styles | 获取风格列表 |
| GET | /api/templates/styles/{key} | 获取风格详情 |

---

## 4. 工作流设计

### 4.1 日记生成工作流（状态机）

```
[START] → vlm_parse → llm_script → img_gen → compose → [DONE]
   ↓         ↓           ↓          ↓         ↓
 failed    failed      failed     failed    failed
```

### 4.2 步骤详情

#### Step 1: vlm_parse - VLM解析

- **输入**：media文件列表
- **处理**：调用豆包VLM (Ark SDK)，提取场景、情绪、物品
- **输出**：metadata_json存入Memory表
- **进度**：25%

#### Step 2: llm_script - LLM生成文案

- **输入**：memory.metadata_json + style_config
- **处理**：调用豆包LLM (Ark SDK)，生成漫画文案和画面描述
- **输出**：{caption, scene_description, bubble_text}
- **进度**：50%

#### Step 3: img_gen - 图像生成

- **输入**：scene_description + style_config
- **处理**：调用即梦Seedream (Ark SDK)生成漫画图
- **输出**：图片文件
- **进度**：75%

#### Step 4: compose - 合成输出

- **输入**：图片 + bubble_text
- **处理**：用Pillow在图片上添加文字气泡
- **输出**：最终漫画图存入Output表
- **进度**：100%

### 4.3 状态流转

- 每个步骤完成后更新Generation.progress (25/50/75/100)
- 失败时记录error_message，status=failed
- 支持重试（从失败步骤继续）

---

## 5. 提示词模板设计

### 5.1 模板文件格式

使用YAML格式，存储在 `templates/styles.yaml`

### 5.2 模板结构

```yaml
styles:
  watercolor:
    name: "水彩手绘"
    description: "柔和的水彩风格，温暖治愈"
    vlm_prompt: "分析这张照片的场景、情绪和关键物品，用温暖治愈的语调描述"
    llm_prompt: "基于以下内容生成一段温馨的日记文案：\n{metadata}\n风格：水彩手绘"
    img_prompt: "水彩手绘风格，{scene_description}，温暖色调，治愈系"
    bubble_style: "圆润可爱"

  manga_jp:
    name: "日式漫画"
    description: "经典日漫风格，线条清晰"
    vlm_prompt: "分析这张照片，识别漫画式的表情和动作"
    llm_prompt: "将以下内容改编成日式漫画风格的旁白：\n{metadata}"
    img_prompt: "日式漫画风格，{scene_description}，清晰线条，动漫风"
    bubble_style: "日式对话框"

  # ... 其他10种风格
```

### 5.3 模板变量

- `{metadata}` - VLM解析的结构化数据
- `{scene_description}` - 场景描述
- `{user_mood}` - 用户选择的情绪
- `{memory_date}` - 记忆日期

### 5.4 模板管理类

```python
class StyleManager:
    def get_style(self, key: str) -> dict
    def list_styles(self) -> list
    def render_prompt(self, key: str, **kwargs) -> str
```

---

## 6. 数据流图

```
用户上传照片+文字
       ↓
   [FastAPI]
       ↓
┌─────────────────────────────────────────┐
│  1. 创建Memory记录 (文字+日期+情绪)      │
│  2. 保存Media文件到本地存储               │
│  3. 创建Generation任务 (status=pending)  │
└─────────────────────────────────────────┘
       ↓
   [异步工作流]
       ↓
┌─────────────────────────────────────────┐
│  Step 1: VLM解析                         │
│  - 调用豆包VLM (Ark SDK)                 │
│  - 提取场景/情绪/物品                     │
│  - 存入Memory.metadata_json              │
│  - 更新progress=25                       │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  Step 2: LLM生成文案                     │
│  - 调用豆包LLM (Ark SDK)                 │
│  - 输入: metadata + style模板            │
│  - 输出: caption, scene_desc, bubble     │
│  - 更新progress=50                       │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  Step 3: 图像生成                        │
│  - 调用即梦Seedream (Ark SDK)            │
│  - 输入: scene_desc + style              │
│  - 输出: 漫画图片                        │
│  - 更新progress=75                       │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│  Step 4: 合成输出                        │
│  - Pillow添加文字气泡                    │
│  - 保存到Output表                        │
│  - 更新progress=100, status=done         │
└─────────────────────────────────────────┘
       ↓
   [SSE推送进度]
       ↓
   用户查看/下载结果
```

### 6.1 Redis用途

- 缓存风格模板列表
- 存储生成任务的实时状态（SSE推送）

---

## 7. 项目结构

```
app/
├── api/                    # FastAPI路由
│   ├── memories.py         # 记忆CRUD
│   ├── media.py            # 媒体上传
│   ├── generations.py      # 生成任务
│   └── templates.py        # 模板查询
├── services/               # AI服务封装
│   ├── vlm_service.py      # VLM解析
│   ├── llm_service.py      # LLM文案
│   ├── img_service.py      # 图像生成
│   └── tts_service.py      # TTS合成
├── workflows/              # 工作流编排
│   ├── base.py             # 基础状态机
│   └── diary.py            # 日记工作流
├── models/                 # SQLAlchemy模型
│   ├── user.py
│   ├── memory.py
│   ├── media.py
│   ├── generation.py
│   └── output.py
├── schemas/                # Pydantic schemas
│   ├── user.py
│   ├── memory.py
│   └── generation.py
├── templates/              # 提示词模板
│   └── styles.yaml         # 12种风格配置
├── config.py               # 配置文件
├── database.py             # 数据库连接
└── main.py                 # FastAPI入口
```

---

## 8. 环境变量配置

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/you_time

# Redis
REDIS_URL=redis://localhost:6379/0

# 火山引擎Ark SDK
ARK_API_KEY=your_ark_api_key

# 火山引擎MaaS SDK (TTS)
VOLC_ACCESSKEY=your_access_key
VOLC_SECRETKEY=your_secret_key

# 豆包模型端点
DOUBAO_ENDPOINT_ID=ep-xxxxx      # LLM推理接入点
DOUBAO_VLM_ENDPOINT_ID=ep-xxxxx  # VLM视觉模型接入点
SEEDREAM_ENDPOINT_ID=ep-xxxxx    # 即梦图像生成接入点
TTS_ENDPOINT_ID=ep-xxxxx         # TTS语音合成接入点

# 文件存储路径
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
```

---

## 9. 依赖包

```txt
# Web Framework
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.18

# Database
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0

# Redis
redis[hiredis]==5.2.1

# AI SDKs
volcenginesdkarkruntime>=1.0.0
volcengine>=1.0.0

# Utilities
python-dotenv==1.0.1
pydantic==2.10.3
pydantic-settings==2.7.0
aiofiles==24.1.0
sse-starlette==2.1.3
pyyaml==6.0.2

# Image Processing
Pillow==11.0.0
```

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 用户可以上传照片和文字创建记忆
- [ ] 用户可以选择风格模板生成漫画
- [ ] 系统能完成VLM解析→LLM文案→图像生成→合成的完整流程
- [ ] 生成结果可以下载查看
- [ ] SSE能实时推送生成进度

### 10.2 技术验收

- [ ] 代码符合FastAPI最佳实践
- [ ] 数据库模型设计合理，有适当索引
- [ ] AI服务调用有错误处理和重试机制
- [ ] 文件上传有大小和类型限制
- [ ] 环境变量配置完整

---

## 11. 后续迭代方向

1. **爽文剧场工作流**：图片轮播 + TTS旁白
2. **用户认证**：抖音小程序登录
3. **社交分享**：一键发布到抖音
4. **知识图谱**：人物关系识别和管理
5. **更多风格**：扩展到20+种视觉风格
6. **视频生成**：接入Seedance 2.0生成短视频
