/**
 * YOU TIME API 服务层
 */

// API基础路径（开发环境使用代理）
const API_BASE = ''

// 风格映射
export const STYLE_MAP = {
  default: 'watercolor',
  warm: 'watercolor',
  cool: 'manga_jp',
  humor: 'cartoon',
  dramatic: 'comic_shuangwen',
}

export const STYLE_NAMES = {
  watercolor: '水彩手绘',
  manga_jp: '日式漫画',
  american_retro: '美式复古',
  cyberpunk: '赛博朋克',
  picture_book: '绘本风',
  ink_wash: '水墨风',
  pixel_art: '像素风',
  oil_painting: '油画风',
  line_drawing: '线稿风',
  cartoon: '卡通风',
  realistic: '写实风',
  fantasy: '奇幻风',
  comic_shuangwen: '高光爽文',
  comic_zhiyu: '治愈温馨',
  comic_timeline: '一天记录',
}

export const POLISH_STYLE_MAP = {
  polished: 'polished',
  wechat: 'moments',
  xiaohongshu: 'xiaohongshu',
}

/**
 * 通用请求方法
 */
async function request(method, path, options = {}) {
  const url = new URL(path, window.location.origin)

  if (options.params) {
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value))
      }
    })
  }

  const headers = {}
  const init = { method, headers }

  if (options.formData) {
    init.body = options.formData
  } else if (options.body) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(options.body)
  }

  const response = await fetch(url.toString(), init)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ==================== 记忆相关 ====================

export function createMemory(data) {
  return request('POST', '/api/memories/', { body: data })
}

export function listMemories(params = {}) {
  return request('GET', '/api/memories/', { params })
}

export function getMemory(memoryId) {
  return request('GET', `/api/memories/${memoryId}`)
}

export function getMemoryMedia(memoryId) {
  return request('GET', `/api/memories/${memoryId}/media`)
}

// ==================== 媒体相关 ====================

export function uploadMedia(memoryId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('POST', '/api/media/upload', { 
    params: { memory_id: memoryId },
    formData 
  })
}

// ==================== 生成任务相关 ====================

export function createGeneration(data) {
  return request('POST', '/api/generations/', { body: data })
}

export function getGeneration(generationId) {
  return request('GET', `/api/generations/${generationId}`)
}

export function listGenerations(params = {}) {
  return request('GET', '/api/generations/', { params })
}

export function updatePrompt(generationId, data) {
  return request('PUT', `/api/generations/${generationId}/prompt`, { body: data })
}

export function polishDiary(generationId, data) {
  return request('POST', `/api/generations/${generationId}/polish-diary`, { body: data })
}

export function getGenerationOutputs(generationId) {
  return request('GET', `/api/generations/${generationId}/outputs`)
}

/**
 * SSE进度监听
 */
export function streamGenerationProgress(generationId, callbacks) {
  const url = `/api/generations/${generationId}/stream`
  const eventSource = new EventSource(url)

  eventSource.addEventListener('progress', (event) => {
    console.log('[SSE] progress raw data:', event.data)
    try {
      const data = JSON.parse(event.data)
      callbacks.onProgress?.(data)
    } catch (e) {
      console.error('[SSE] JSON parse error:', e, 'raw:', event.data)
    }
  })

  eventSource.addEventListener('complete', (event) => {
    console.log('[SSE] complete raw data:', event.data)
    try {
      const data = JSON.parse(event.data)
      callbacks.onComplete?.(data)
      eventSource.close()
    } catch (e) {
      console.error('[SSE] JSON parse error:', e, 'raw:', event.data)
    }
  })

  eventSource.addEventListener('error', (event) => {
    console.error('[SSE] error event:', event)
    callbacks.onError?.(event)
    eventSource.close()
  })

  return eventSource
}

// ==================== 视频生成相关 ====================

export function createVideoGeneration(data) {
  return request('POST', '/api/generations/video', { body: data })
}

export function getVideoScript(generationId) {
  return request('GET', `/api/generations/${generationId}/video-script`)
}

export function updateVideoScript(generationId, script) {
  return request('PUT', `/api/generations/${generationId}/video-script`, {
    body: { script }
  })
}

export function confirmVideoScript(generationId) {
  return request('POST', `/api/generations/${generationId}/confirm-video`)
}

export function listVideoStyles() {
  return request('GET', '/api/generations/video-styles')
}

// ==================== 模板相关 ====================

export function confirmPrompt(generationId, finalPrompt) {
  return request('POST', `/api/generations/${generationId}/confirm`, {
    body: { final_prompt: finalPrompt }
  })
}

export function listStyles() {
  return request('GET', '/api/templates/styles')
}

// ==================== 独立文本润色 ====================

export function polishText(data) {
  return request('POST', '/api/generations/polish-text', { body: data })
}

// ==================== 一日漫画 ====================

export function createDailyDiary(memoryDate) {
  return request('POST', '/api/generations/daily-diary', { body: { memory_date: memoryDate } })
}
