/**
 * YOU TIME API TypeScript类型定义
 * 版本: v1.0.0
 * 更新日期: 2026-05-16
 */

// ==================== 基础类型 ====================

/**
 * UUID字符串类型
 */
export type UUID = string;

/**
 * ISO 8601日期时间字符串
 */
export type ISO8601DateTime = string;

/**
 * ISO 8601日期字符串 (YYYY-MM-DD)
 */
export type ISO8601Date = string;

// ==================== 用户相关 ====================

/**
 * 用户基础信息
 */
export interface UserBase {
  nickname?: string;
  avatar?: string;
}

/**
 * 创建用户请求
 */
export interface UserCreate extends UserBase {
  openid: string;
  unionid?: string;
  phone?: string;
}

/**
 * 用户响应
 */
export interface UserResponse extends UserBase {
  id: UUID;
  openid: string;
  created_at: ISO8601DateTime;
}

// ==================== 记忆相关 ====================

/**
 * 记忆基础信息
 */
export interface MemoryBase {
  content_text?: string;
  memory_date: ISO8601Date;
  mood_tag?: string;
}

/**
 * 创建记忆请求
 */
export interface MemoryCreate extends MemoryBase {}

/**
 * 记忆响应
 */
export interface MemoryResponse extends MemoryBase {
  id: UUID;
  user_id: UUID;
  metadata_json?: any;
  created_at: ISO8601DateTime;
}

/**
 * 记忆列表响应
 */
export interface MemoryList {
  memories: MemoryResponse[];
  total: number;
}

/**
 * 心情标签枚举
 */
export type MoodTag =
  | 'happy'
  | 'sad'
  | 'excited'
  | 'calm'
  | 'angry'
  | 'surprised'
  | 'grateful'
  | 'nostalgic';

// ==================== 媒体相关 ====================

/**
 * 媒体响应
 */
export interface MediaResponse {
  id: UUID;
  memory_id: UUID;
  file_path: string;
  file_type: string;
  original_filename?: string;
  taken_at?: ISO8601DateTime;
  sort_order?: number;
  created_at: ISO8601DateTime;
}

export type MemoryMediaList = MediaResponse[];

/**
 * 支持的媒体文件类型
 */
export type AllowedMediaType = 'image/jpeg' | 'image/png' | 'image/webp';

// ==================== 生成任务相关 ====================

/**
 * 生成类型
 */
export type GenerationType = 'diary';

/**
 * 生成任务状态
 */
export type GenerationStatus = 'processing' | 'pending_confirmation' | 'done' | 'failed';

/**
 * 生成任务阶段
 */
export type GenerationStage = 'vlm_parse' | 'img_gen';

/**
 * 创建生成任务请求
 */
export interface GenerationCreate {
  memory_ids: UUID[];
  type?: GenerationType;
  style_key: string;
}

/**
 * 生成任务响应
 */
export interface GenerationResponse {
  id: UUID;
  user_id: UUID;
  memory_ids: UUID[];
  type: GenerationType;
  style_key: string;
  status: GenerationStatus;
  progress: number;
  current_step?: string;
  error_message?: string;
  created_at: ISO8601DateTime;
  completed_at?: ISO8601DateTime;

  // 两阶段工作流字段
  stage?: GenerationStage;
  vlm_raw_metadata?: any;
  user_edited_prompt?: string;
  llm_polished_prompt?: string;
  final_prompt?: string;
  prompt_confirmed: boolean;
}

/**
 * 生成进度信息
 */
export interface GenerationProgress {
  generation_id: UUID;
  status: GenerationStatus;
  progress: number;
  current_step?: string;
}

/**
 * 用户编辑提示词请求
 */
export interface PromptUpdate {
  user_edited_prompt: string;
}

/**
 * LLM润色请求
 */
export interface PromptPolish {
  prompt: string;
}

/**
 * 用户确认提示词请求
 */
export interface PromptConfirm {
  final_prompt: string;
}

/**
 * 日记润色请求
 */
export interface DiaryPolish {
  diary_text: string;
  style_key: string;
}

/**
 * 日记润色响应
 */
export interface DiaryPolishResponse {
  original_text: string;
  polished_text: string;
  style_key: string;
  style_name: string;
}

/**
 * 情绪提取请求
 */
export interface EmotionExtract {
  diary_text: string;
}

/**
 * 情绪提取响应
 */
export interface EmotionResult {
  primary_emotion?: string;
  intensity?: number;
  secondary_emotion?: string;
  bgm_vibe?: string;
  color_palette?: string;
  weather_mood?: string;
  [key: string]: any;
}

// ==================== 模板相关 ====================

/**
 * 风格模板
 */
export interface Style {
  key: string;
  name: string;
  description: string;
  prompt_template: string;
  [key: string]: any;
}

// ==================== SSE事件相关 ====================

/**
 * SSE事件类型
 */
export type SSEEventType = 'progress' | 'complete' | 'error';

/**
 * SSE进度事件数据
 */
export interface SSEProgressData {
  generation_id: UUID;
  status: GenerationStatus;
  stage: GenerationStage;
  progress: number;
  current_step?: string;
  vlm_raw_metadata?: any;
  user_edited_prompt?: string;
  llm_polished_prompt?: string;
  final_prompt?: string;
}

/**
 * SSE错误事件数据
 */
export interface SSEErrorData {
  error: string;
}

// ==================== API响应错误 ====================

/**
 * API错误响应
 */
export interface ApiError {
  detail: string;
}

// ==================== 分页参数 ====================

/**
 * 分页查询参数
 */
export interface PaginationParams {
  skip?: number;
  limit?: number;
  date?: ISO8601Date;
  start_date?: ISO8601Date;
  end_date?: ISO8601Date;
}

// ==================== API客户端类型 ====================

/**
 * API客户端接口
 */
export interface YouTimeApiClient {
  // 记忆相关
  createMemory(data: MemoryCreate): Promise<MemoryResponse>;
  listMemories(params?: PaginationParams): Promise<MemoryList>;
  getMemory(memoryId: UUID): Promise<MemoryResponse>;
  getMemoryMedia(memoryId: UUID): Promise<MemoryMediaList>;

  // 媒体相关
  uploadMedia(memoryId: UUID, file: File): Promise<MediaResponse>;
  getMedia(mediaId: UUID): Promise<MediaResponse>;

  // 生成任务相关
  createGeneration(data: GenerationCreate): Promise<GenerationResponse>;
  listGenerations(params?: PaginationParams): Promise<GenerationResponse[]>;
  getGeneration(generationId: UUID): Promise<GenerationResponse>;
  updatePrompt(generationId: UUID, data: PromptUpdate): Promise<GenerationResponse>;
  polishPrompt(generationId: UUID, data: PromptPolish): Promise<GenerationResponse>;
  confirmPrompt(generationId: UUID, data: PromptConfirm): Promise<GenerationResponse>;
  polishDiary(generationId: UUID, data: DiaryPolish): Promise<DiaryPolishResponse>;
  extractEmotion(generationId: UUID, data: EmotionExtract): Promise<EmotionResult>;
  streamGenerationProgress(generationId: UUID): EventSource;

  // 模板相关
  listStyles(): Promise<Style[]>;
  getStyle(styleKey: string): Promise<Style>;
  listPolishStyles(): Promise<Style[]>;
}
