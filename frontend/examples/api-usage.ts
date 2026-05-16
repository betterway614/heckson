/**
 * YOU TIME API使用示例
 * 版本: v1.0.0
 * 更新日期: 2026-05-16
 *
 * 本文件展示了如何在前端项目中使用YOU TIME API
 */

import { youTimeApi } from '../api/client';
import type {
  MemoryCreate,
  MemoryResponse,
  GenerationCreate,
  GenerationResponse,
  SSEProgressData,
} from '../types/api';

// ==================== 示例1: 创建记忆并上传图片 ====================

/**
 * 示例1: 创建记忆并上传图片
 */
export async function example1_createMemoryWithImage() {
  try {
    // 1. 创建记忆
    const memoryData: MemoryCreate = {
      content_text: '今天和朋友去了海边，看到了美丽的日落',
      memory_date: '2026-05-15',
      mood_tag: 'happy',
    };

    const memory: MemoryResponse = await youTimeApi.createMemory(memoryData);
    console.log('记忆创建成功:', memory);

    // 2. 上传图片
    // 假设有一个文件输入元素
    const fileInput = document.querySelector<HTMLInputElement>('#image-input');
    if (fileInput?.files?.[0]) {
      const media = await youTimeApi.uploadMedia(memory.id, fileInput.files[0]);
      console.log('图片上传成功:', media);
    }

    return memory;
  } catch (error) {
    console.error('创建记忆失败:', error);
    throw error;
  }
}

// ==================== 示例2: 获取记忆列表 ====================

/**
 * 示例2: 获取记忆列表
 */
export async function example2_listMemories() {
  try {
    // 获取前10条记忆
    const result = await youTimeApi.listMemories({ skip: 0, limit: 10 });
    console.log('记忆列表:', result.memories);
    console.log('总数:', result.total);

    return result;
  } catch (error) {
    console.error('获取记忆列表失败:', error);
    throw error;
  }
}

// ==================== 示例3: 创建生成任务并监听进度 ====================

/**
 * 示例3: 创建生成任务并监听进度
 */
export async function example3_createGenerationWithProgress() {
  try {
    // 1. 创建生成任务
    const generationData: GenerationCreate = {
      memory_ids: [
        '550e8400-e29b-41d4-a716-446655440000',
        '550e8400-e29b-41d4-a716-446655440001',
      ],
      type: 'diary',
      style_key: 'watercolor',
    };

    const generation: GenerationResponse = await youTimeApi.createGeneration(generationData);
    console.log('生成任务创建成功:', generation);

    // 2. 监听进度
    const eventSource = youTimeApi.streamGenerationProgress(generation.id);

    // 监听进度事件
    eventSource.addEventListener('progress', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      console.log('进度更新:', {
        progress: data.progress,
        status: data.status,
        stage: data.stage,
        currentStep: data.current_step,
      });

      // 更新UI进度条
      updateProgressBar(data.progress);
    });

    // 监听完成事件
    eventSource.addEventListener('complete', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      console.log('任务完成:', data);

      // 如果状态是pending_confirmation，说明VLM解析完成
      if (data.status === 'pending_confirmation') {
        console.log('VLM解析完成，请用户确认提示词');
        showPromptConfirmation(data);
      }

      // 关闭SSE连接
      eventSource.close();
    });

    // 监听错误事件
    eventSource.addEventListener('error', (event) => {
      console.error('SSE错误:', event);
      eventSource.close();
    });

    return generation;
  } catch (error) {
    console.error('创建生成任务失败:', error);
    throw error;
  }
}

// ==================== 示例4: 完整的两阶段工作流 ====================

/**
 * 示例4: 完整的两阶段工作流
 */
export async function example4_completeWorkflow() {
  try {
    // 阶段1: 创建生成任务
    const generationData: GenerationCreate = {
      memory_ids: ['550e8400-e29b-41d4-a716-446655440000'],
      type: 'diary',
      style_key: 'watercolor',
    };

    const generation = await youTimeApi.createGeneration(generationData);
    console.log('阶段1 - 生成任务创建成功');

    // 等待VLM解析完成
    const vlmResult = await waitForVlmParsing(generation.id);
    console.log('阶段1 - VLM解析完成:', vlmResult);

    // 用户编辑提示词
    const userEditedPrompt = '一个温暖的海边日落场景，两个朋友坐在沙滩上';
    await youTimeApi.updatePrompt(generation.id, {
      user_edited_prompt: userEditedPrompt,
    });
    console.log('阶段1 - 用户编辑提示词完成');

    // 可选: LLM润色
    const polishedResult = await youTimeApi.polishPrompt(generation.id, {
      prompt: userEditedPrompt,
    });
    console.log('阶段1 - LLM润色完成:', polishedResult.llm_polished_prompt);

    // 用户确认提示词
    const finalPrompt = polishedResult.llm_polished_prompt || userEditedPrompt;
    await youTimeApi.confirmPrompt(generation.id, {
      final_prompt: finalPrompt,
    });
    console.log('阶段2 - 开始图片生成');

    // 监听图片生成进度
    const finalResult = await waitForImageGeneration(generation.id);
    console.log('阶段2 - 图片生成完成:', finalResult);

    return finalResult;
  } catch (error) {
    console.error('工作流执行失败:', error);
    throw error;
  }
}

// ==================== 示例5: 获取风格模板 ====================

/**
 * 示例5: 获取风格模板
 */
export async function example5_getStyles() {
  try {
    // 获取所有风格
    const styles = await youTimeApi.listStyles();
    console.log('可用风格:', styles);

    // 获取特定风格详情
    if (styles.length > 0) {
      const styleDetail = await youTimeApi.getStyle(styles[0].key);
      console.log('风格详情:', styleDetail);
    }

    return styles;
  } catch (error) {
    console.error('获取风格失败:', error);
    throw error;
  }
}

// ==================== 辅助函数 ====================

/**
 * 等待VLM解析完成
 */
async function waitForVlmParsing(generationId: string): Promise<GenerationResponse> {
  return new Promise((resolve, reject) => {
    const eventSource = youTimeApi.streamGenerationProgress(generationId);

    eventSource.addEventListener('progress', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      console.log('VLM解析进度:', data.progress);
    });

    eventSource.addEventListener('complete', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      eventSource.close();

      if (data.status === 'pending_confirmation') {
        // 获取完整的生成任务信息
        youTimeApi.getGeneration(generationId).then(resolve).catch(reject);
      } else {
        reject(new Error(`VLM解析失败: ${data.status}`));
      }
    });

    eventSource.addEventListener('error', (event) => {
      eventSource.close();
      reject(new Error('SSE连接错误'));
    });
  });
}

/**
 * 等待图片生成完成
 */
async function waitForImageGeneration(generationId: string): Promise<GenerationResponse> {
  return new Promise((resolve, reject) => {
    const eventSource = youTimeApi.streamGenerationProgress(generationId);

    eventSource.addEventListener('progress', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      console.log('图片生成进度:', data.progress);
      updateProgressBar(data.progress);
    });

    eventSource.addEventListener('complete', (event) => {
      const data: SSEProgressData = JSON.parse(event.data);
      eventSource.close();

      if (data.status === 'done') {
        youTimeApi.getGeneration(generationId).then(resolve).catch(reject);
      } else {
        reject(new Error(`图片生成失败: ${data.status}`));
      }
    });

    eventSource.addEventListener('error', (event) => {
      eventSource.close();
      reject(new Error('SSE连接错误'));
    });
  });
}

/**
 * 更新进度条 (示例实现)
 */
function updateProgressBar(progress: number) {
  const progressBar = document.querySelector<HTMLDivElement>('#progress-bar');
  if (progressBar) {
    progressBar.style.width = `${progress}%`;
    progressBar.textContent = `${progress}%`;
  }
}

/**
 * 显示提示词确认界面 (示例实现)
 */
function showPromptConfirmation(data: SSEProgressData) {
  // 这里应该显示一个UI界面，让用户查看VLM解析结果并编辑提示词
  console.log('显示提示词确认界面');
  console.log('VLM解析结果:', data.vlm_raw_metadata);

  // 示例: 创建一个简单的确认界面
  const container = document.querySelector('#generation-container');
  if (container) {
    container.innerHTML = `
      <div class="prompt-confirmation">
        <h3>VLM解析完成</h3>
        <div class="vlm-result">
          <pre>${JSON.stringify(data.vlm_raw_metadata, null, 2)}</pre>
        </div>
        <div class="prompt-editor">
          <label>编辑提示词:</label>
          <textarea id="user-prompt" rows="4">${data.vlm_raw_metadata?.description || ''}</textarea>
        </div>
        <div class="actions">
          <button id="btn-polish">LLM润色</button>
          <button id="btn-confirm">确认生成</button>
        </div>
      </div>
    `;
  }
}

// ==================== React Hook示例 ====================

/**
 * React Hook: 使用生成任务
 *
 * 使用示例:
 * ```tsx
 * const { generation, isLoading, error, createGeneration, confirmPrompt } = useGeneration();
 * ```
 */
export function useGeneration() {
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createGeneration = async (data: GenerationCreate) => {
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
  };

  const updatePrompt = async (prompt: string) => {
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
  };

  const confirmPrompt = async (finalPrompt: string) => {
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
  };

  return {
    generation,
    isLoading,
    error,
    createGeneration,
    updatePrompt,
    confirmPrompt,
  };
}

// 注意: 这里需要导入React的useState，实际使用时需要根据项目框架调整
// import { useState } from 'react';
