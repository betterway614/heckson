# YOU TIME - AI人生放映厅

一个基于 AI 的个人记忆管理和多媒体生成平台，让用户可以记录、回顾和重新体验人生中的美好时刻。

## 功能特性

- **记忆管理** - 创建、存储和检索个人记忆
- **AI 图像生成** - 根据记忆描述生成精美图片
- **AI 视频生成** - 根据记忆内容生成 15 秒视频回忆录
- **语音合成 (TTS)** - 将文字转换为语音
- **语音识别 (ASR)** - 将语音转换为文字
- **视觉语言模型 (VLM)** - 从图片中提取信息
- **日记工作流** - 自动生成日记内容

## 技术栈

- **后端框架**: FastAPI
- **数据库**: PostgreSQL (asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
- **AI 服务**: 集成多种 AI API

## 项目结构

```
heckson/
├── app/
│   ├── api/          # API 路由
│   ├── models/       # 数据库模型
│   ├── schemas/      # Pydantic 数据模式
│   ├── services/     # 业务逻辑服务
│   ├── templates/    # 模板配置
│   ├── utils/        # 工具函数
│   └── workflows/    # 工作流定义
├── frontend/         # 前端代码
├── scripts/          # 工具脚本
├── tests/            # 测试文件
└── docs/             # 文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload
```

服务将在 http://localhost:8000 启动

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 测试

```bash
# 运行烟雾测试
python tests/test_smoke_full.py

# 运行集成测试
python tests/test_integration_db.py

# 运行视频生成测试
python -m pytest tests/test_video_workflow.py -v
```

## 视频生成功能

### 功能说明
- 支持按时间范围选择记忆（最近7天/30天/90天/自定义）
- LLM 自动生成视频脚本，支持用户编辑确认
- 调用 wan2.7 模型生成 15 秒视频
- 支持多种预设风格：电影感、纪录片、温馨回忆、活力四射
- 支持多种分辨率：720p/1080p，横屏/竖屏

### API 端点
- `GET /api/generations/video-styles` - 获取视频风格列表
- `POST /api/generations/video` - 创建视频生成任务
- `GET /api/generations/{id}/video-script` - 获取视频脚本
- `PUT /api/generations/{id}/video-script` - 更新视频脚本
- `POST /api/generations/{id}/confirm-video` - 确认脚本，生成视频

### 使用流程
1. 选择时间范围和视频风格
2. 系统自动从数据库读取该时间范围内的记忆
3. LLM 根据记忆内容生成视频脚本
4. 用户预览并编辑脚本（可选）
5. 确认后调用 wan2.7 模型生成视频
6. 视频生成完成后可预览和下载

## 许可证

MIT License
