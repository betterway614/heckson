# YOU TIME API 接口文档

> AI人生放映厅后端API接口文档 v1.0.0

## 目录

- [基础信息](#基础信息)
- [认证说明](#认证说明)
- [通用响应格式](#通用响应格式)
- [错误码说明](#错误码说明)
- [API接口列表](#api接口列表)
  - [记忆管理 (Memories)](#记忆管理-memories)
  - [媒体管理 (Media)](#媒体管理-media)
  - [生成任务 (Generations)](#生成任务-generations)
  - [模板管理 (Templates)](#模板管理-templates)

---

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1.0.0
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证说明

当前版本使用临时用户ID进行测试，后续将集成微信小程序登录认证。

## 通用响应格式

### 成功响应

```json
{
  "id": "uuid",
  "field1": "value1",
  "field2": "value2",
  "created_at": "2026-05-16T10:00:00"
}
```

### 错误响应

```json
{
  "detail": "Error message"
}
```

## 错误码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

---

## API接口列表

### 记忆管理 (Memories)

#### 1. 创建记忆

**POST** `/api/memories/`

创建一条新的记忆记录。

**请求参数 (Request Body)**

```typescript
interface MemoryCreate {
  content_text?: string;      // 记忆文本内容，可选
  memory_date: string;        // 记忆日期，格式：YYYY-MM-DD，必填
  mood_tag?: string;          // 心情标签，可选
}
```

**请求示例**

```json
{
  "content_text": "今天和朋友去了海边，看到了美丽的日落",
  "memory_date": "2026-05-15",
  "mood_tag": "happy"
}
```

**响应参数 (Response)**

```typescript
interface MemoryResponse {
  id: string;                 // UUID，记忆唯一标识
  user_id: string;            // UUID，用户ID
  content_text?: string;      // 记忆文本内容
  memory_date: string;        // 记忆日期
  mood_tag?: string;          // 心情标签
  metadata_json?: any;        // 元数据JSON
  created_at: string;         // 创建时间，ISO 8601格式
}
```

**响应示例**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "content_text": "今天和朋友去了海边，看到了美丽的日落",
  "memory_date": "2026-05-15",
  "mood_tag": "happy",
  "metadata_json": null,
  "created_at": "2026-05-16T10:00:00"
}
```

---

#### 2. 获取记忆列表

**GET** `/api/memories/`

获取当前用户的记忆列表，支持分页。

**查询参数 (Query Parameters)**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| skip | integer | 否 | 0 | 跳过的记录数 |
| limit | integer | 否 | 20 | 返回的记录数，最大100 |

**请求示例**

```
GET /api/memories/?skip=0&limit=10
```

**响应参数 (Response)**

```typescript
interface MemoryList {
  memories: MemoryResponse[];  // 记忆列表
  total: number;               // 总记录数
}
```

**响应示例**

```json
{
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "00000000-0000-0000-0000-000000000001",
      "content_text": "今天和朋友去了海边",
      "memory_date": "2026-05-15",
      "mood_tag": "happy",
      "metadata_json": null,
      "created_at": "2026-05-16T10:00:00"
    }
  ],
  "total": 1
}
```

---

#### 3. 获取记忆详情

**GET** `/api/memories/{memory_id}`

根据记忆ID获取记忆详情。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| memory_id | string (UUID) | 是 | 记忆唯一标识 |

**请求示例**

```
GET /api/memories/550e8400-e29b-41d4-a716-446655440000
```

**响应参数 (Response)**

同 `MemoryResponse`

**错误响应**

```json
{
  "detail": "Memory not found"
}
```

---

### 媒体管理 (Media)

#### 1. 上传媒体文件

**POST** `/api/media/upload`

上传媒体文件（图片）到指定记忆。

**请求参数 (Form Data)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| memory_id | string (UUID) | 是 | 关联的记忆ID |
| file | File | 是 | 图片文件，支持：image/jpeg, image/png, image/webp |

**请求示例 (cURL)**

```bash
curl -X POST "http://localhost:8000/api/media/upload" \
  -F "memory_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "file=@/path/to/image.jpg"
```

**响应参数 (Response)**

```typescript
interface MediaResponse {
  id: string;                  // UUID，媒体唯一标识
  memory_id: string;           // UUID，关联的记忆ID
  file_path: string;           // 文件存储路径
  file_type: string;           // 文件类型，如：image
  original_filename?: string;  // 原始文件名
  created_at: string;          // 创建时间，ISO 8601格式
}
```

**响应示例**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_path": "uploads/images/abc123.jpg",
  "file_type": "image",
  "original_filename": "sunset.jpg",
  "created_at": "2026-05-16T10:05:00"
}
```

**错误响应**

```json
{
  "detail": "File type not allowed"
}
```

---

#### 2. 获取媒体信息

**GET** `/api/media/{media_id}`

根据媒体ID获取媒体信息。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| media_id | string (UUID) | 是 | 媒体唯一标识 |

**请求示例**

```
GET /api/media/660e8400-e29b-41d4-a716-446655440001
```

**响应参数 (Response)**

同 `MediaResponse`

**错误响应**

```json
{
  "detail": "Media not found"
}
```

---

### 生成任务 (Generations)

#### 1. 创建生成任务

**POST** `/api/generations/`

创建AI生成任务，自动触发阶段1：VLM解析。

**请求参数 (Request Body)**

```typescript
interface GenerationCreate {
  memory_ids: string[];        // UUID数组，关联的记忆ID列表，必填
  type?: string;               // 生成类型，默认："diary"
  style_key: string;           // 风格标识，必填
}
```

**请求示例**

```json
{
  "memory_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "type": "diary",
  "style_key": "watercolor"
}
```

**响应参数 (Response)**

```typescript
interface GenerationResponse {
  id: string;                          // UUID，生成任务唯一标识
  user_id: string;                     // UUID，用户ID
  memory_ids: string[];                // UUID数组，关联的记忆ID列表
  type: string;                        // 生成类型
  style_key: string;                   // 风格标识
  status: string;                      // 任务状态
  progress: number;                    // 进度百分比 (0-100)
  current_step?: string;               // 当前步骤说明
  error_message?: string;              // 错误信息
  created_at: string;                  // 创建时间
  completed_at?: string;               // 完成时间

  // 两阶段工作流字段
  stage?: string;                      // 当前阶段：vlm_parse | img_gen
  vlm_raw_metadata?: any;              // VLM解析的原始元数据
  user_edited_prompt?: string;         // 用户编辑的提示词
  llm_polished_prompt?: string;        // LLM润色后的提示词
  final_prompt?: string;               // 最终确认的提示词
  prompt_confirmed: boolean;           // 提示词是否已确认
}
```

**任务状态 (status) 说明**

| 状态 | 说明 |
|------|------|
| processing | 处理中 |
| pending_confirmation | 等待用户确认提示词 |
| done | 完成 |
| failed | 失败 |

**阶段 (stage) 说明**

| 阶段 | 说明 |
|------|------|
| vlm_parse | 阶段1：VLM解析记忆 |
| img_gen | 阶段2：图片生成 |

**响应示例**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "memory_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "type": "diary",
  "style_key": "watercolor",
  "status": "processing",
  "progress": 0,
  "current_step": null,
  "error_message": null,
  "created_at": "2026-05-16T10:10:00",
  "completed_at": null,
  "stage": "vlm_parse",
  "vlm_raw_metadata": null,
  "user_edited_prompt": null,
  "llm_polished_prompt": null,
  "final_prompt": null,
  "prompt_confirmed": false
}
```

---

#### 2. 获取生成任务状态

**GET** `/api/generations/{generation_id}`

根据生成任务ID获取任务状态和详情。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| generation_id | string (UUID) | 是 | 生成任务唯一标识 |

**请求示例**

```
GET /api/generations/770e8400-e29b-41d4-a716-446655440002
```

**响应参数 (Response)**

同 `GenerationResponse`

**错误响应**

```json
{
  "detail": "Generation not found"
}
```

---

#### 3. 更新用户编辑的提示词

**PUT** `/api/generations/{generation_id}/prompt`

用户查看VLM解析结果后，可以自定义编辑提示词。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| generation_id | string (UUID) | 是 | 生成任务唯一标识 |

**请求参数 (Request Body)**

```typescript
interface PromptUpdate {
  user_edited_prompt: string;  // 用户编辑的提示词，必填
}
```

**请求示例**

```json
{
  "user_edited_prompt": "一个温暖的海边日落场景，两个朋友坐在沙滩上，天空被染成橙红色"
}
```

**响应参数 (Response)**

同 `GenerationResponse`

**错误响应**

```json
{
  "detail": "Generation not ready for prompt editing"
}
```

---

#### 4. LLM润色提示词（可选）

**POST** `/api/generations/{generation_id}/polish`

用户可以选择让LLM润色自己编辑的提示词。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| generation_id | string (UUID) | 是 | 生成任务唯一标识 |

**请求参数 (Request Body)**

```typescript
interface PromptPolish {
  prompt: string;              // 待润色的提示词，必填
}
```

**请求示例**

```json
{
  "prompt": "一个温暖的海边日落场景"
}
```

**响应参数 (Response)**

同 `GenerationResponse`，其中 `llm_polished_prompt` 字段为润色后的提示词。

**错误响应**

```json
{
  "detail": "Generation not ready for prompt polishing"
}
```

---

#### 5. 确认提示词 - 触发图片生成

**POST** `/api/generations/{generation_id}/confirm`

用户确认最终提示词后，触发阶段2：图片生成工作流。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| generation_id | string (UUID) | 是 | 生成任务唯一标识 |

**请求参数 (Request Body)**

```typescript
interface PromptConfirm {
  final_prompt: string;        // 最终确认的提示词，必填
}
```

**请求示例**

```json
{
  "final_prompt": "一个温暖的海边日落场景，两个朋友坐在沙滩上，天空被染成橙红色，水彩风格"
}
```

**响应参数 (Response)**

同 `GenerationResponse`，状态变为 `processing`，阶段变为 `img_gen`。

**错误响应**

```json
{
  "detail": "Generation not ready for confirmation"
}
```

---

#### 6. SSE推送生成进度

**GET** `/api/generations/{generation_id}/stream`

通过Server-Sent Events实时推送生成任务的进度。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| generation_id | string (UUID) | 是 | 生成任务唯一标识 |

**请求示例**

```
GET /api/generations/770e8400-e29b-41d4-a716-446655440002/stream
```

**响应格式 (SSE)**

```
event: progress
data: {"generation_id":"770e8400-...","status":"processing","stage":"vlm_parse","progress":50,"current_step":"Analyzing images","vlm_raw_metadata":null,"user_edited_prompt":null,"llm_polished_prompt":null,"final_prompt":null}

event: progress
data: {"generation_id":"770e8400-...","status":"pending_confirmation","stage":"vlm_parse","progress":100,"current_step":"VLM parsing completed","vlm_raw_metadata":{...},"user_edited_prompt":null,"llm_polished_prompt":null,"final_prompt":null}

event: complete
data: {"generation_id":"770e8400-...","status":"pending_confirmation","stage":"vlm_parse","progress":100,"current_step":"VLM parsing completed","vlm_raw_metadata":{...},"user_edited_prompt":null,"llm_polished_prompt":null,"final_prompt":null}
```

**事件类型说明**

| 事件 | 说明 |
|------|------|
| progress | 进度更新 |
| complete | 任务完成（成功或失败） |
| error | 发生错误 |

---

### 模板管理 (Templates)

#### 1. 获取风格列表

**GET** `/api/templates/styles`

获取所有可用的风格模板列表。

**请求示例**

```
GET /api/templates/styles
```

**响应参数 (Response)**

```typescript
interface Style {
  key: string;                 // 风格标识
  name: string;                // 风格名称
  description: string;         // 风格描述
  prompt_template: string;     // 提示词模板
  // ... 其他风格配置
}

// 响应为 Style 数组
Style[]
```

**响应示例**

```json
[
  {
    "key": "watercolor",
    "name": "水彩风格",
    "description": "柔和的水彩画风格",
    "prompt_template": "..."
  },
  {
    "key": "oil_painting",
    "name": "油画风格",
    "description": "经典的油画风格",
    "prompt_template": "..."
  }
]
```

---

#### 2. 获取风格详情

**GET** `/api/templates/styles/{style_key}`

根据风格标识获取风格详情。

**路径参数 (Path Parameters)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| style_key | string | 是 | 风格标识 |

**请求示例**

```
GET /api/templates/styles/watercolor
```

**响应参数 (Response)**

同 `Style` 对象

**错误响应**

```json
{
  "detail": "Style not found"
}
```

---

## 附录

### 常用心情标签 (mood_tag)

| 标签 | 说明 |
|------|------|
| happy | 开心 |
| sad | 难过 |
| excited | 兴奋 |
| calm | 平静 |
| angry | 生气 |
| surprised | 惊讶 |
| grateful | 感激 |
| nostalgic | 怀旧 |

### 生成类型 (type)

| 类型 | 说明 |
|------|------|
| diary | 日记生成 |

### 两阶段工作流说明

1. **阶段1：VLM解析 (vlm_parse)**
   - 用户提交记忆和图片
   - VLM（视觉语言模型）分析图片内容
   - 生成结构化元数据
   - 状态变为 `pending_confirmation`

2. **阶段2：图片生成 (img_gen)**
   - 用户编辑/确认提示词
   - 调用图片生成模型
   - 生成最终图片
   - 状态变为 `done`

---

## 前端集成示例

### JavaScript/TypeScript 示例

```typescript
// 创建记忆
const createMemory = async (data: MemoryCreate): Promise<MemoryResponse> => {
  const response = await fetch('/api/memories/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  return response.json();
};

// 上传媒体文件
const uploadMedia = async (memoryId: string, file: File): Promise<MediaResponse> => {
  const formData = new FormData();
  formData.append('memory_id', memoryId);
  formData.append('file', file);

  const response = await fetch('/api/media/upload', {
    method: 'POST',
    body: formData,
  });
  return response.json();
};

// 创建生成任务
const createGeneration = async (data: GenerationCreate): Promise<GenerationResponse> => {
  const response = await fetch('/api/generations/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  return response.json();
};

// 监听生成进度 (SSE)
const listenGenerationProgress = (generationId: string) => {
  const eventSource = new EventSource(`/api/generations/${generationId}/stream`);

  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress);
    console.log('Status:', data.status);
    console.log('Stage:', data.stage);
  });

  eventSource.addEventListener('complete', (event) => {
    const data = JSON.parse(event.data);
    console.log('Completed:', data);
    eventSource.close();
  });

  eventSource.addEventListener('error', (event) => {
    console.error('Error:', event);
    eventSource.close();
  });

  return eventSource;
};

// 确认提示词
const confirmPrompt = async (generationId: string, finalPrompt: string): Promise<GenerationResponse> => {
  const response = await fetch(`/api/generations/${generationId}/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ final_prompt: finalPrompt }),
  });
  return response.json();
};
```

### 完整工作流示例

```typescript
// 1. 创建记忆
const memory = await createMemory({
  content_text: "今天和朋友去了海边",
  memory_date: "2026-05-15",
  mood_tag: "happy"
});

// 2. 上传图片
const media = await uploadMedia(memory.id, imageFile);

// 3. 创建生成任务
const generation = await createGeneration({
  memory_ids: [memory.id],
  type: "diary",
  style_key: "watercolor"
});

// 4. 监听进度
const eventSource = listenGenerationProgress(generation.id);

// 5. 等待VLM解析完成（status变为pending_confirmation）
// 6. 用户编辑提示词
await updatePrompt(generation.id, "用户编辑的提示词");

// 7. 可选：LLM润色
await polishPrompt(generation.id, "用户编辑的提示词");

// 8. 确认提示词
await confirmPrompt(generation.id, "最终确认的提示词");

// 9. 继续监听进度直到完成
```

---

**文档版本**: v1.0.0
**最后更新**: 2026-05-16
**维护团队**: YOU TIME 开发团队
