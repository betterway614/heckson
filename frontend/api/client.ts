/**
 * YOU TIME API客户端实现
 * 版本: v1.0.0
 * 更新日期: 2026-05-16
 */

import type {
  UUID,
  MemoryCreate,
  MemoryResponse,
  MemoryList,
  MemoryMediaList,
  MediaResponse,
  GenerationCreate,
  GenerationResponse,
  PromptUpdate,
  PromptPolish,
  PromptConfirm,
  DiaryPolish,
  DiaryPolishResponse,
  EmotionExtract,
  EmotionResult,
  Style,
  PaginationParams,
  SSEProgressData,
  SSEErrorData,
  ApiError,
  YouTimeApiClient,
} from '../types/api';

/**
 * API客户端配置
 */
export interface YouTimeApiConfig {
  baseUrl?: string;
  timeout?: number;
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: YouTimeApiConfig = {
  baseUrl: (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
};

/**
 * YOU TIME API客户端
 */
export class YouTimeApi implements YouTimeApiClient {
  private config: YouTimeApiConfig;

  constructor(config?: YouTimeApiConfig) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 通用请求方法
   */
  private async request<T>(
    method: string,
    path: string,
    options?: {
      body?: any;
      params?: Record<string, any>;
      formData?: FormData;
    }
  ): Promise<T> {
    const url = new URL(path, this.config.baseUrl);

    // 添加查询参数
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {};

    // 如果不是FormData，设置Content-Type
    if (!options?.formData) {
      headers['Content-Type'] = 'application/json';
    }

    const requestInit: RequestInit = {
      method,
      headers,
    };

    // 设置请求体
    if (options?.formData) {
      requestInit.body = options.formData;
    } else if (options?.body) {
      requestInit.body = JSON.stringify(options.body);
    }

    // 设置超时
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
    requestInit.signal = controller.signal;

    try {
      const response = await fetch(url.toString(), requestInit);
      clearTimeout(timeoutId);

      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  // ==================== 记忆相关 ====================

  /**
   * 创建记忆
   */
  async createMemory(data: MemoryCreate): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('POST', '/api/memories/', {
      body: data,
    });
  }

  /**
   * 获取记忆列表
   */
  async listMemories(params?: PaginationParams): Promise<MemoryList> {
    return this.request<MemoryList>('GET', '/api/memories/', {
      params,
    });
  }

  /**
   * 获取记忆详情
   */
  async getMemory(memoryId: UUID): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('GET', `/api/memories/${memoryId}`);
  }

  /**
   * 获取记忆关联媒体
   */
  async getMemoryMedia(memoryId: UUID): Promise<MemoryMediaList> {
    return this.request<MemoryMediaList>('GET', `/api/memories/${memoryId}/media`);
  }

  // ==================== 媒体相关 ====================

  /**
   * 上传媒体文件
   */
  async uploadMedia(memoryId: UUID, file: File): Promise<MediaResponse> {
    const formData = new FormData();
    formData.append('memory_id', memoryId);
    formData.append('file', file);

    return this.request<MediaResponse>('POST', '/api/media/upload', {
      formData,
    });
  }

  /**
   * 获取媒体信息
   */
  async getMedia(mediaId: UUID): Promise<MediaResponse> {
    return this.request<MediaResponse>('GET', `/api/media/${mediaId}`);
  }

  // ==================== 生成任务相关 ====================

  /**
   * 创建生成任务
   */
  async createGeneration(data: GenerationCreate): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('POST', '/api/generations/', {
      body: data,
    });
  }

  /**
   * 获取生成任务列表
   */
  async listGenerations(params?: PaginationParams): Promise<GenerationResponse[]> {
    return this.request<GenerationResponse[]>('GET', '/api/generations/', {
      params,
    });
  }

  /**
   * 获取生成任务状态
   */
  async getGeneration(generationId: UUID): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('GET', `/api/generations/${generationId}`);
  }

  /**
   * 更新用户编辑的提示词
   */
  async updatePrompt(generationId: UUID, data: PromptUpdate): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('PUT', `/api/generations/${generationId}/prompt`, {
      body: data,
    });
  }

  /**
   * LLM润色提示词
   */
  async polishPrompt(generationId: UUID, data: PromptPolish): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('POST', `/api/generations/${generationId}/polish`, {
      body: data,
    });
  }

  /**
   * 确认提示词
   */
  async confirmPrompt(generationId: UUID, data: PromptConfirm): Promise<GenerationResponse> {
    return this.request<GenerationResponse>('POST', `/api/generations/${generationId}/confirm`, {
      body: data,
    });
  }

  /**
   * 日记文本润色
   */
  async polishDiary(generationId: UUID, data: DiaryPolish): Promise<DiaryPolishResponse> {
    return this.request<DiaryPolishResponse>('POST', `/api/generations/${generationId}/polish-diary`, {
      body: data,
    });
  }

  /**
   * 提取情绪标签
   */
  async extractEmotion(generationId: UUID, data: EmotionExtract): Promise<EmotionResult> {
    return this.request<EmotionResult>('POST', `/api/generations/${generationId}/extract-emotion`, {
      body: data,
    });
  }

  /**
   * 监听生成进度 (SSE)
   */
  streamGenerationProgress(generationId: UUID): EventSource {
    const url = `${this.config.baseUrl}/api/generations/${generationId}/stream`;
    return new EventSource(url);
  }

  // ==================== 模板相关 ====================

  /**
   * 获取风格列表
   */
  async listStyles(): Promise<Style[]> {
    return this.request<Style[]>('GET', '/api/templates/styles');
  }

  /**
   * 获取风格详情
   */
  async getStyle(styleKey: string): Promise<Style> {
    return this.request<Style>('GET', `/api/templates/styles/${styleKey}`);
  }

  /**
   * 获取日记润色风格列表
   */
  async listPolishStyles(): Promise<Style[]> {
    return this.request<Style[]>('GET', '/api/generations/polish-styles');
  }
}

/**
 * 创建默认API客户端实例
 */
export const createYouTimeApi = (config?: YouTimeApiConfig): YouTimeApi => {
  return new YouTimeApi(config);
};

/**
 * 默认API客户端实例
 */
export const youTimeApi = createYouTimeApi();
