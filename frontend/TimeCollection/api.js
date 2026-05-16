/**
 * YOU TIME API 服务层
 * 版本: v1.0.0
 */

const API_BASE_URL = 'http://localhost:8000';

// 风格key映射：前端值 → 后端key
const STYLE_MAP = {
    'default': 'watercolor',
    'warm': 'watercolor',
    'cool': 'manga_jp',
    'humor': 'cartoon',
    'dramatic': 'comic_shuangwen'
};

// 润色风格映射：前端tab → 后端key
const POLISH_STYLE_MAP = {
    'original': null,
    'polished': 'polished',
    'wechat': 'moments',
    'xiaohongshu': 'xiaohongshu'
};

/**
 * 通用API请求方法
 */
async function apiRequest(method, path, options = {}) {
    const url = new URL(path, API_BASE_URL);

    if (options.params) {
        Object.entries(options.params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, String(value));
            }
        });
    }

    const headers = {};
    const requestInit = { method, headers };

    if (options.formData) {
        requestInit.body = options.formData;
    } else if (options.body) {
        headers['Content-Type'] = 'application/json';
        requestInit.body = JSON.stringify(options.body);
    }

    const response = await fetch(url.toString(), requestInit);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ==================== 记忆相关 ====================

async function createMemory(data) {
    return apiRequest('POST', '/api/memories/', { body: data });
}

async function listMemories(params = {}) {
    return apiRequest('GET', '/api/memories/', { params });
}

async function getMemory(memoryId) {
    return apiRequest('GET', `/api/memories/${memoryId}`);
}

async function getMemoryMedia(memoryId) {
    return apiRequest('GET', `/api/memories/${memoryId}/media`);
}

// ==================== 媒体相关 ====================

async function uploadMedia(memoryId, file) {
    const formData = new FormData();
    formData.append('memory_id', memoryId);
    formData.append('file', file);
    return apiRequest('POST', '/api/media/upload', { formData });
}

async function getMedia(mediaId) {
    return apiRequest('GET', `/api/media/${mediaId}`);
}

// ==================== 生成任务相关 ====================

async function createGeneration(data) {
    return apiRequest('POST', '/api/generations/', { body: data });
}

async function getGeneration(generationId) {
    return apiRequest('GET', `/api/generations/${generationId}`);
}

async function listGenerations(params = {}) {
    return apiRequest('GET', '/api/generations/', { params });
}

async function updatePrompt(generationId, data) {
    return apiRequest('PUT', `/api/generations/${generationId}/prompt`, { body: data });
}

async function polishPrompt(generationId, data) {
    return apiRequest('POST', `/api/generations/${generationId}/polish`, { body: data });
}

async function confirmPrompt(generationId, data) {
    return apiRequest('POST', `/api/generations/${generationId}/confirm`, { body: data });
}

async function polishDiary(generationId, data) {
    return apiRequest('POST', `/api/generations/${generationId}/polish-diary`, { body: data });
}

async function extractEmotion(generationId, data) {
    return apiRequest('POST', `/api/generations/${generationId}/extract-emotion`, { body: data });
}

async function getGenerationOutputs(generationId) {
    return apiRequest('GET', `/api/generations/${generationId}/outputs`);
}

/**
 * 监听生成进度 (SSE)
 */
function streamGenerationProgress(generationId, callbacks) {
    const url = `${API_BASE_URL}/api/generations/${generationId}/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        callbacks.onProgress?.(data);
    });

    eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        callbacks.onComplete?.(data);
        eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
        callbacks.onError?.(event);
        eventSource.close();
    });

    return eventSource;
}

// ==================== 模板相关 ====================

async function listStyles() {
    return apiRequest('GET', '/api/templates/styles');
}

async function getStyle(styleKey) {
    return apiRequest('GET', `/api/templates/styles/${styleKey}`);
}

async function listPolishStyles() {
    return apiRequest('GET', '/api/generations/polish-styles');
}

// ==================== 视频生成相关 ====================

async function createVideoGeneration(data) {
    return apiRequest('POST', '/api/generations/video', { body: data });
}

async function getVideoScript(generationId) {
    return apiRequest('GET', `/api/generations/${generationId}/video-script`);
}

async function updateVideoScript(generationId, script) {
    return apiRequest('PUT', `/api/generations/${generationId}/video-script`, { body: { script } });
}

async function confirmVideoGeneration(generationId) {
    return apiRequest('POST', `/api/generations/${generationId}/confirm-video`);
}

async function listVideoStyles() {
    return apiRequest('GET', '/api/generations/video-styles');
}
