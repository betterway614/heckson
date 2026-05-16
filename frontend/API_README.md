# YOU TIME 前端API集成指南

> AI人生放映厅前端API集成文档 v1.0.0

## 文件结构

```
frontend/
├── types/
│   └── api.ts              # TypeScript类型定义
├── api/
│   └── client.ts           # API客户端实现
├── examples/
│   └── api-usage.ts        # 使用示例
└── API_README.md           # 本文档
```

## 快速开始

### 1. 安装依赖

确保你的前端项目支持TypeScript和Fetch API。

### 2. 引入API客户端

```typescript
import { youTimeApi } from './api/client';
// 或者
import { createYouTimeApi } from './api/client';

// 使用自定义配置
const api = createYouTimeApi({
  baseUrl: 'https://your-api-domain.com',
  timeout: 60000,
});
```

### 3. 基本使用

#### 创建记忆

```typescript
import type { MemoryCreate } from './types/api';

const memory = await youTimeApi.createMemory({
  content_text: '今天和朋友去了海边',
  memory_date: '2026-05-15',
  mood_tag: 'happy',
});

console.log('记忆ID:', memory.id);
```

#### 上传图片

```typescript
const fileInput = document.querySelector<HTMLInputElement>('#image-input');
if (fileInput?.files?.[0]) {
  const media = await youTimeApi.uploadMedia(memory.id, fileInput.files[0]);
  console.log('图片URL:', media.file_path);
}
```

#### 创建生成任务

```typescript
import type { GenerationCreate } from './types/api';

const generation = await youTimeApi.createGeneration({
  memory_ids: [memory.id],
  type: 'diary',
  style_key: 'watercolor',
});

console.log('生成任务ID:', generation.id);
```

#### 监听生成进度

```typescript
const eventSource = youTimeApi.streamGenerationProgress(generation.id);

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log('进度:', data.progress);
  console.log('状态:', data.status);
  console.log('阶段:', data.stage);
});

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('完成:', data);
  eventSource.close();
});
```

## 完整工作流示例

```typescript
import { youTimeApi } from './api/client';
import type { GenerationCreate, SSEProgressData } from './types/api';

async function completeWorkflow() {
  try {
    // 1. 创建记忆
    const memory = await youTimeApi.createMemory({
      content_text: '今天和朋友去了海边',
      memory_date: '2026-05-15',
      mood_tag: 'happy',
    });

    // 2. 上传图片
    const fileInput = document.querySelector<HTMLInputElement>('#image-input');
    if (fileInput?.files?.[0]) {
      await youTimeApi.uploadMedia(memory.id, fileInput.files[0]);
    }

    // 3. 创建生成任务
    const generation = await youTimeApi.createGeneration({
      memory_ids: [memory.id],
      type: 'diary',
      style_key: 'watercolor',
    });

    // 4. 等待VLM解析完成
    await new Promise<void>((resolve, reject) => {
      const eventSource = youTimeApi.streamGenerationProgress(generation.id);

      eventSource.addEventListener('complete', (event) => {
        const data: SSEProgressData = JSON.parse(event.data);
        eventSource.close();

        if (data.status === 'pending_confirmation') {
          resolve();
        } else {
          reject(new Error(`VLM解析失败: ${data.status}`));
        }
      });

      eventSource.addEventListener('error', () => {
        eventSource.close();
        reject(new Error('SSE连接错误'));
      });
    });

    // 5. 用户编辑提示词
    await youTimeApi.updatePrompt(generation.id, {
      user_edited_prompt: '一个温暖的海边日落场景',
    });

    // 6. 可选: LLM润色
    const polished = await youTimeApi.polishPrompt(generation.id, {
      prompt: '一个温暖的海边日落场景',
    });

    // 7. 确认提示词
    await youTimeApi.confirmPrompt(generation.id, {
      final_prompt: polished.llm_polished_prompt || '一个温暖的海边日落场景',
    });

    // 8. 等待图片生成完成
    const result = await new Promise<any>((resolve, reject) => {
      const eventSource = youTimeApi.streamGenerationProgress(generation.id);

      eventSource.addEventListener('progress', (event) => {
        const data: SSEProgressData = JSON.parse(event.data);
        console.log('生成进度:', data.progress);
      });

      eventSource.addEventListener('complete', (event) => {
        const data: SSEProgressData = JSON.parse(event.data);
        eventSource.close();
        resolve(data);
      });

      eventSource.addEventListener('error', () => {
        eventSource.close();
        reject(new Error('图片生成失败'));
      });
    });

    console.log('生成完成:', result);
    return result;
  } catch (error) {
    console.error('工作流执行失败:', error);
    throw error;
  }
}
```

## React集成示例

### 自定义Hook

```typescript
import { useState, useCallback } from 'react';
import { youTimeApi } from './api/client';
import type {
  GenerationCreate,
  GenerationResponse,
  SSEProgressData,
} from './types/api';

export function useGeneration() {
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createGeneration = useCallback(async (data: GenerationCreate) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await youTimeApi.createGeneration(data);
      setGeneration(result);

      // 开始监听进度
      const eventSource = youTimeApi.streamGenerationProgress(result.id);

      eventSource.addEventListener('progress', (event) => {
        const progressData: SSEProgressData = JSON.parse(event.data);
        setGeneration((prev) => (prev ? { ...prev, ...progressData } : null));
      });

      eventSource.addEventListener('complete', (event) => {
        const progressData: SSEProgressData = JSON.parse(event.data);
        setGeneration((prev) => (prev ? { ...prev, ...progressData } : null));
        eventSource.close();
      });

      eventSource.addEventListener('error', () => {
        eventSource.close();
      });

      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updatePrompt = useCallback(async (prompt: string) => {
    if (!generation) return;

    setIsLoading(true);
    try {
      const result = await youTimeApi.updatePrompt(generation.id, {
        user_edited_prompt: prompt,
      });
      setGeneration(result);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [generation]);

  const confirmPrompt = useCallback(async (finalPrompt: string) => {
    if (!generation) return;

    setIsLoading(true);
    try {
      const result = await youTimeApi.confirmPrompt(generation.id, {
        final_prompt: finalPrompt,
      });
      setGeneration(result);

      // 重新开始监听进度
      const eventSource = youTimeApi.streamGenerationProgress(generation.id);

      eventSource.addEventListener('progress', (event) => {
        const progressData: SSEProgressData = JSON.parse(event.data);
        setGeneration((prev) => (prev ? { ...prev, ...progressData } : null));
      });

      eventSource.addEventListener('complete', (event) => {
        const progressData: SSEProgressData = JSON.parse(event.data);
        setGeneration((prev) => (prev ? { ...prev, ...progressData } : null));
        eventSource.close();
      });

      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [generation]);

  return {
    generation,
    isLoading,
    error,
    createGeneration,
    updatePrompt,
    confirmPrompt,
  };
}
```

### React组件示例

```tsx
import React, { useState } from 'react';
import { useGeneration } from './hooks/useGeneration';

export function GenerationForm() {
  const { generation, isLoading, error, createGeneration, updatePrompt, confirmPrompt } = useGeneration();
  const [prompt, setPrompt] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    await createGeneration({
      memory_ids: ['memory-id-1', 'memory-id-2'],
      type: 'diary',
      style_key: 'watercolor',
    });
  };

  const handleConfirm = async () => {
    await confirmPrompt(prompt);
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <button type="submit" disabled={isLoading}>
          {isLoading ? '处理中...' : '开始生成'}
        </button>
      </form>

      {error && <div className="error">{error.message}</div>}

      {generation && (
        <div>
          <h3>生成任务状态</h3>
          <p>状态: {generation.status}</p>
          <p>进度: {generation.progress}%</p>
          <p>阶段: {generation.stage}</p>

          {generation.status === 'pending_confirmation' && (
            <div>
              <h4>确认提示词</h4>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                placeholder="编辑提示词..."
              />
              <button onClick={handleConfirm} disabled={isLoading}>
                确认生成
              </button>
            </div>
          )}

          {generation.status === 'done' && (
            <div>
              <h4>生成完成!</h4>
              <pre>{JSON.stringify(generation.vlm_raw_metadata, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## API参考

详细的API文档请参考: [API_DOCUMENTATION.md](../API_DOCUMENTATION.md)

## 类型定义

完整的TypeScript类型定义请参考: [types/api.ts](./types/api.ts)

## 常见问题

### 1. 如何处理SSE连接断开？

EventSource会自动尝试重新连接。如果需要手动处理，可以在error事件中实现重连逻辑。

### 2. 如何取消正在进行的生成任务？

目前API不支持取消任务。如果需要取消，可以忽略SSE事件并关闭EventSource连接。

### 3. 如何处理大文件上传？

当前实现使用FormData上传文件。对于大文件，建议：
- 前端进行文件压缩
- 后端配置适当的文件大小限制
- 实现上传进度显示

### 4. 如何在生产环境配置API地址？

```typescript
const api = createYouTimeApi({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 60000,
});
```

## 更新日志

### v1.0.0 (2026-05-16)
- 初始版本发布
- 支持记忆管理API
- 支持媒体上传API
- 支持生成任务API
- 支持SSE进度推送
- 支持风格模板API

---

**维护团队**: YOU TIME 开发团队
**最后更新**: 2026-05-16
