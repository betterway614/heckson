# YOU TIME API脚本生成总结

> 生成日期: 2026-05-16
> 版本: v1.0.0

## 概述

根据YOU TIME（AI人生放映厅）的产品功能设计，已生成完整的后端API脚本和对应的出入参数文档，用于前端团队对接。

## 生成的文件列表

### 1. API接口文档
**文件**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

**内容**:
- 完整的API接口说明
- 所有端点的请求/响应参数
- 错误码说明
- 前端集成示例
- 工作流说明

**包含的API模块**:
- 记忆管理 (Memories) - 3个接口
- 媒体管理 (Media) - 2个接口
- 生成任务 (Generations) - 6个接口
- 模板管理 (Templates) - 2个接口

**总计**: 13个API接口

---

### 2. TypeScript类型定义
**文件**: [frontend/types/api.ts](frontend/types/api.ts)

**内容**:
- 所有数据模型的TypeScript类型定义
- 请求/响应接口类型
- 枚举类型定义
- SSE事件类型
- API客户端接口定义

**主要类型**:
- `MemoryCreate` / `MemoryResponse` / `MemoryList`
- `MediaResponse`
- `GenerationCreate` / `GenerationResponse` / `GenerationProgress`
- `PromptUpdate` / `PromptPolish` / `PromptConfirm`
- `Style`
- `SSEProgressData` / `SSEErrorData`
- `YouTimeApiClient`

---

### 3. API客户端实现
**文件**: [frontend/api/client.ts](frontend/api/client.ts)

**内容**:
- 完整的API客户端类实现
- 所有API方法的封装
- 错误处理
- 超时控制
- FormData支持（文件上传）
- SSE连接管理

**主要功能**:
- 通用请求方法
- 记忆CRUD操作
- 媒体文件上传
- 生成任务管理
- SSE进度监听
- 风格模板查询

---

### 4. 使用示例代码
**文件**: [frontend/examples/api-usage.ts](frontend/examples/api-usage.ts)

**内容**:
- 5个完整的使用示例
- React Hook示例
- 辅助函数实现
- 完整工作流示例

**示例列表**:
1. 创建记忆并上传图片
2. 获取记忆列表
3. 创建生成任务并监听进度
4. 完整的两阶段工作流
5. 获取风格模板

---

### 5. 前端集成指南
**文件**: [frontend/API_README.md](frontend/API_README.md)

**内容**:
- 快速开始指南
- 完整工作流示例
- React集成示例
- 自定义Hook实现
- 常见问题解答
- 更新日志

---

## API接口总览

### 记忆管理 (Memories)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/memories/ | 创建记忆 |
| GET | /api/memories/ | 获取记忆列表 |
| GET | /api/memories/{memory_id} | 获取记忆详情 |

### 媒体管理 (Media)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/media/upload | 上传媒体文件 |
| GET | /api/media/{media_id} | 获取媒体信息 |

### 生成任务 (Generations)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/generations/ | 创建生成任务 |
| GET | /api/generations/{generation_id} | 获取生成任务状态 |
| PUT | /api/generations/{generation_id}/prompt | 更新用户编辑的提示词 |
| POST | /api/generations/{generation_id}/polish | LLM润色提示词 |
| POST | /api/generations/{generation_id}/confirm | 确认提示词 |
| GET | /api/generations/{generation_id}/stream | SSE推送生成进度 |

### 模板管理 (Templates)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/templates/styles | 获取风格列表 |
| GET | /api/templates/styles/{style_key} | 获取风格详情 |

---

## 核心数据模型

### Memory (记忆)

```typescript
interface Memory {
  id: UUID;
  user_id: UUID;
  content_text?: string;
  memory_date: string; // YYYY-MM-DD
  mood_tag?: string;
  metadata_json?: any;
  created_at: string; // ISO 8601
}
```

### Media (媒体)

```typescript
interface Media {
  id: UUID;
  memory_id: UUID;
  file_path: string;
  file_type: string;
  original_filename?: string;
  created_at: string; // ISO 8601
}
```

### Generation (生成任务)

```typescript
interface Generation {
  id: UUID;
  user_id: UUID;
  memory_ids: UUID[];
  type: string;
  style_key: string;
  status: 'processing' | 'pending_confirmation' | 'done' | 'failed';
  progress: number; // 0-100
  current_step?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;

  // 两阶段工作流字段
  stage?: 'vlm_parse' | 'img_gen';
  vlm_raw_metadata?: any;
  user_edited_prompt?: string;
  llm_polished_prompt?: string;
  final_prompt?: string;
  prompt_confirmed: boolean;
}
```

### Style (风格模板)

```typescript
interface Style {
  key: string;
  name: string;
  description: string;
  prompt_template: string;
  [key: string]: any;
}
```

---

## 两阶段工作流说明

### 阶段1: VLM解析 (vlm_parse)

1. 用户提交记忆和图片
2. 创建生成任务，状态为 `processing`
3. VLM（视觉语言模型）分析图片内容
4. 生成结构化元数据
5. 状态变为 `pending_confirmation`
6. 用户可以查看、编辑提示词
7. 可选: LLM润色提示词

### 阶段2: 图片生成 (img_gen)

1. 用户确认最终提示词
2. 状态变为 `processing`，阶段变为 `img_gen`
3. 调用图片生成模型
4. 生成最终图片
5. 状态变为 `done`

---

## 前端集成步骤

### 步骤1: 复制文件

将以下文件复制到前端项目:

```
frontend/
├── types/
│   └── api.ts
├── api/
│   └── client.ts
└── examples/
    └── api-usage.ts (可选，参考用)
```

### 步骤2: 配置API地址

修改 `frontend/api/client.ts` 中的默认配置:

```typescript
const DEFAULT_CONFIG: YouTimeApiConfig = {
  baseUrl: 'https://your-api-domain.com', // 修改为实际API地址
  timeout: 30000,
};
```

### 步骤3: 引入并使用

```typescript
import { youTimeApi } from './api/client';
import type { MemoryCreate, GenerationCreate } from './types/api';

// 使用API
const memory = await youTimeApi.createMemory({
  content_text: '测试记忆',
  memory_date: '2026-05-15',
  mood_tag: 'happy',
});
```

---

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (异步)
- **语言**: Python 3.10+
- **API风格**: RESTful

### 前端 (建议)
- **语言**: TypeScript
- **框架**: React / Vue / Next.js (任选)
- **HTTP客户端**: Fetch API
- **SSE**: EventSource API

---

## 注意事项

1. **认证机制**: 当前版本使用临时用户ID，后续需集成微信小程序登录
2. **文件上传**: 支持 image/jpeg, image/png, image/webp 格式
3. **SSE连接**: 建议实现重连机制处理网络中断
4. **错误处理**: 所有API错误都返回 `{ detail: string }` 格式
5. **分页**: 默认每页20条，最大100条

---

## 后续优化建议

1. **认证集成**: 实现微信小程序登录认证
2. **文件上传优化**: 支持大文件分片上传、断点续传
3. **缓存策略**: 实现API响应缓存
4. **离线支持**: 实现离线队列和同步机制
5. **类型安全**: 生成OpenAPI规范，自动生成类型定义
6. **测试覆盖**: 编写API集成测试

---

## 联系方式

如有问题，请联系YOU TIME开发团队。

---

**文档版本**: v1.0.0
**最后更新**: 2026-05-16
**生成工具**: Claude Code
