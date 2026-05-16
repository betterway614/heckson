<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { youTimeApi } from '../api/client';
import type { EmotionResult, GenerationResponse, MemoryResponse, Style } from '../types/api';

type ViewKey = 'today' | 'diary' | 'story' | 'collection';
type PendingFile = { file: File; previewUrl: string };

const STYLE_MAP: Record<string, string> = {
  default: 'watercolor',
  warm: 'watercolor',
  cool: 'manga_jp',
  humor: 'cartoon',
  dramatic: 'comic_shuangwen',
};

const POLISH_STYLE_MAP: Record<string, string | null> = {
  original: null,
  polished: 'polished',
  wechat: 'moments',
  xiaohongshu: 'xiaohongshu',
};

const views: Array<{ key: ViewKey; label: string }> = [
  { key: 'today', label: '今日记录' },
  { key: 'diary', label: '日记' },
  { key: 'story', label: '故事详情' },
  { key: 'collection', label: '故事集' },
];

const styleOptions = [
  { key: 'warm', label: '温暖治愈' },
  { key: 'cool', label: '高冷文艺' },
  { key: 'humor', label: '幽默风趣' },
  { key: 'dramatic', label: '戏剧张力' },
];

const polishTabs = [
  { key: 'original', label: '原文' },
  { key: 'polished', label: '润色稿' },
  { key: 'wechat', label: '朋友圈' },
  { key: 'xiaohongshu', label: '小红书' },
];

const activeView = ref<ViewKey>('today');
const memoryText = ref('');
const selectedStyle = ref('warm');
const pendingFiles = ref<PendingFile[]>([]);
const todayMemories = ref<MemoryResponse[]>([]);
const currentGeneration = ref<GenerationResponse | null>(null);
const generationStatus = ref('');
const generationProgress = ref(0);
const isSavingMemory = ref(false);
const isGenerating = ref(false);
const statusMessage = ref('');
const styles = ref<Style[]>([]);

const selectedDate = ref(new Date().toISOString().slice(0, 10));
const diaryMemories = ref<MemoryResponse[]>([]);
const diaryGenerations = ref<GenerationResponse[]>([]);
const diaryLoading = ref(false);

const activeStoryTab = ref('original');
const storyText = ref('暂无故事内容');
const editedStoryText = ref('');
const emotion = ref<EmotionResult | null>(null);
const storyLoading = ref(false);

const storyGroups = ref<Array<{ date: string; memories: MemoryResponse[] }>>([]);
const collectionLoading = ref(false);

const totalPendingFiles = computed(() => pendingFiles.value.length);
const canGenerate = computed(() => todayMemories.value.length > 0 && !isGenerating.value);
const currentStyleKey = computed(() => STYLE_MAP[selectedStyle.value] || 'watercolor');

function setView(view: ViewKey) {
  activeView.value = view;
  if (view === 'diary') {
    void loadDiaryByDate();
  }
  if (view === 'collection') {
    void loadStoryCollection();
  }
}

function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  const images = files.filter((file) => file.type.startsWith('image/'));
  pendingFiles.value.push(...images.map((file) => ({
    file,
    previewUrl: URL.createObjectURL(file),
  })));
  input.value = '';
}

function removeFile(index: number) {
  const item = pendingFiles.value[index];
  if (item) {
    URL.revokeObjectURL(item.previewUrl);
  }
  pendingFiles.value.splice(index, 1);
}

async function saveMemory() {
  if (!memoryText.value.trim() && pendingFiles.value.length === 0) {
    statusMessage.value = '请先输入回忆内容或选择图片。';
    return;
  }

  isSavingMemory.value = true;
  statusMessage.value = '';

  try {
    const memory = await youTimeApi.createMemory({
      content_text: memoryText.value.trim() || undefined,
      memory_date: new Date().toISOString().slice(0, 10),
    });

    for (const item of pendingFiles.value) {
      await youTimeApi.uploadMedia(memory.id, item.file);
      URL.revokeObjectURL(item.previewUrl);
    }

    todayMemories.value.unshift(memory);
    memoryText.value = '';
    pendingFiles.value = [];
    statusMessage.value = '回忆已保存，可以继续记录或生成今天的故事。';
  } catch (error) {
    statusMessage.value = error instanceof Error ? error.message : '保存失败，请重试。';
  } finally {
    isSavingMemory.value = false;
  }
}

async function createStoryGeneration() {
  if (!canGenerate.value) {
    statusMessage.value = '请先保存至少一条记忆。';
    return;
  }

  isGenerating.value = true;
  generationProgress.value = 0;
  generationStatus.value = '正在创建生成任务';
  statusMessage.value = '';

  try {
    const generation = await youTimeApi.createGeneration({
      memory_ids: todayMemories.value.map((memory) => memory.id),
      type: 'diary',
      style_key: currentStyleKey.value,
    });
    currentGeneration.value = generation;
    listenForProgress(generation.id);
  } catch (error) {
    generationStatus.value = '';
    statusMessage.value = error instanceof Error ? error.message : '生成任务创建失败。';
    isGenerating.value = false;
  }
}

function listenForProgress(generationId: string) {
  const source = youTimeApi.streamGenerationProgress(generationId);

  source.addEventListener('progress', (event) => {
    const data = JSON.parse((event as MessageEvent).data) as GenerationResponse;
    generationProgress.value = data.progress || 0;
    generationStatus.value = data.current_step || data.stage || data.status;
  });

  source.addEventListener('complete', (event) => {
    const data = JSON.parse((event as MessageEvent).data) as GenerationResponse;
    currentGeneration.value = data;
    generationProgress.value = data.progress || generationProgress.value;
    generationStatus.value = data.status;
    storyText.value = extractDiaryText(data);
    editedStoryText.value = storyText.value;
    isGenerating.value = false;
    source.close();
    setView('story');
  });

  source.addEventListener('error', () => {
    generationStatus.value = '生成进度连接中断';
    isGenerating.value = false;
    source.close();
  });
}

function extractDiaryText(generation: GenerationResponse | null) {
  const raw = generation?.vlm_raw_metadata;
  if (!raw) {
    return generation?.final_prompt || generation?.user_edited_prompt || '暂无故事内容';
  }
  if (typeof raw === 'string') {
    return raw;
  }
  const diary = raw.diary || raw.text || raw.summary || raw.content;
  return typeof diary === 'string' ? diary : JSON.stringify(diary || raw, null, 2);
}

async function loadDiaryByDate() {
  diaryLoading.value = true;
  try {
    const [memories, generations] = await Promise.all([
      youTimeApi.listMemories({ date: selectedDate.value }),
      youTimeApi.listGenerations({ date: selectedDate.value }),
    ]);
    diaryMemories.value = memories.memories;
    diaryGenerations.value = generations;
  } finally {
    diaryLoading.value = false;
  }
}

async function openGeneration(generation: GenerationResponse) {
  currentGeneration.value = await youTimeApi.getGeneration(generation.id);
  storyText.value = extractDiaryText(currentGeneration.value);
  editedStoryText.value = storyText.value;
  activeStoryTab.value = 'original';
  setView('story');
}

async function switchStoryTab(tab: string) {
  activeStoryTab.value = tab;
  const generation = currentGeneration.value;
  if (!generation) {
    storyText.value = '请先创建或打开一个生成任务。';
    return;
  }

  const original = extractDiaryText(generation);
  if (tab === 'original') {
    storyText.value = original;
    return;
  }

  const styleKey = POLISH_STYLE_MAP[tab];
  if (!styleKey) {
    return;
  }

  storyLoading.value = true;
  try {
    const result = await youTimeApi.polishDiary(generation.id, {
      diary_text: original,
      style_key: styleKey,
    });
    storyText.value = result.polished_text;
    editedStoryText.value = result.polished_text;
  } finally {
    storyLoading.value = false;
  }
}

async function saveEditedStory() {
  const generation = currentGeneration.value;
  if (!generation || !editedStoryText.value.trim()) {
    return;
  }
  currentGeneration.value = await youTimeApi.updatePrompt(generation.id, {
    user_edited_prompt: editedStoryText.value.trim(),
  });
  storyText.value = editedStoryText.value.trim();
}

async function extractEmotion() {
  const generation = currentGeneration.value;
  if (!generation) {
    return;
  }
  emotion.value = await youTimeApi.extractEmotion(generation.id, {
    diary_text: storyText.value,
  });
}

async function loadStoryCollection() {
  collectionLoading.value = true;
  try {
    const endDate = new Date();
    const startDate = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000);
    const result = await youTimeApi.listMemories({
      start_date: startDate.toISOString().slice(0, 10),
      end_date: endDate.toISOString().slice(0, 10),
      limit: 100,
    });
    const grouped = result.memories.reduce<Record<string, MemoryResponse[]>>((acc, memory) => {
      acc[memory.memory_date] = acc[memory.memory_date] || [];
      acc[memory.memory_date].push(memory);
      return acc;
    }, {});
    storyGroups.value = Object.entries(grouped).map(([date, memories]) => ({ date, memories }));
  } finally {
    collectionLoading.value = false;
  }
}

onMounted(async () => {
  try {
    styles.value = await youTimeApi.listStyles();
  } catch {
    styles.value = [];
  }
});
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">AI Life Cinema</p>
        <h1>YOU TIME</h1>
      </div>
      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="view in views"
          :key="view.key"
          :class="{ active: activeView === view.key }"
          type="button"
          @click="setView(view.key)"
        >
          {{ view.label }}
        </button>
      </nav>
      <div class="api-health">
        <span>API</span>
        <strong>{{ styles.length ? '已连接' : '待连接' }}</strong>
      </div>
    </aside>

    <section v-if="activeView === 'today'" class="workspace">
      <header class="page-header">
        <p class="eyebrow">Capture</p>
        <h2>记录今天的记忆</h2>
      </header>

      <div class="two-column">
        <section class="panel input-panel">
          <label for="memory-text">回忆内容</label>
          <textarea id="memory-text" v-model="memoryText" maxlength="500" placeholder="写下今天发生的一个片段"></textarea>
          <div class="input-footer">
            <span>{{ memoryText.length }}/500</span>
            <label class="upload-button">
              选择图片
              <input type="file" accept="image/*" multiple @change="onFilesSelected" />
            </label>
          </div>

          <div v-if="pendingFiles.length" class="preview-grid">
            <figure v-for="(item, index) in pendingFiles" :key="item.previewUrl">
              <img :src="item.previewUrl" alt="待上传图片预览" />
              <button type="button" @click="removeFile(index)">移除</button>
            </figure>
          </div>

          <button class="primary-action" type="button" :disabled="isSavingMemory" @click="saveMemory">
            {{ isSavingMemory ? '保存中' : '确认记录' }}
          </button>
          <p v-if="statusMessage" class="status-text">{{ statusMessage }}</p>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Timeline</p>
              <h3>今日事件</h3>
            </div>
            <span>{{ todayMemories.length }} 条</span>
          </div>
          <ol class="event-list">
            <li v-for="memory in todayMemories" :key="memory.id">
              <span>{{ new Date(memory.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}</span>
              <p>{{ memory.content_text || '图片记忆' }}</p>
            </li>
          </ol>
          <p v-if="!todayMemories.length" class="empty-state">保存后的记忆会出现在这里。</p>

          <div class="generation-controls">
            <label for="style-select">故事风格</label>
            <select id="style-select" v-model="selectedStyle">
              <option v-for="style in styleOptions" :key="style.key" :value="style.key">{{ style.label }}</option>
            </select>
            <button class="primary-action" type="button" :disabled="!canGenerate" @click="createStoryGeneration">
              {{ isGenerating ? 'AI 生成中' : '完成今天的故事' }}
            </button>
            <div v-if="isGenerating || generationStatus" class="progress-block">
              <progress :value="generationProgress" max="100"></progress>
              <span>{{ generationStatus }}</span>
            </div>
          </div>
        </section>
      </div>
    </section>

    <section v-else-if="activeView === 'diary'" class="workspace">
      <header class="page-header">
        <p class="eyebrow">Diary</p>
        <h2>按日期查看记忆</h2>
      </header>
      <section class="panel">
        <div class="date-row">
          <input v-model="selectedDate" type="date" @change="loadDiaryByDate" />
          <button type="button" @click="loadDiaryByDate">刷新</button>
        </div>
        <p v-if="diaryLoading" class="status-text">加载中...</p>
        <div class="diary-grid">
          <article>
            <h3>记忆时间线</h3>
            <ol class="event-list">
              <li v-for="memory in diaryMemories" :key="memory.id">
                <span>{{ new Date(memory.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}</span>
                <p>{{ memory.content_text || '图片记忆' }}</p>
              </li>
            </ol>
            <p v-if="!diaryMemories.length && !diaryLoading" class="empty-state">这个日期还没有记忆。</p>
          </article>
          <article>
            <h3>生成记录</h3>
            <button
              v-for="generation in diaryGenerations"
              :key="generation.id"
              class="generation-item"
              type="button"
              @click="openGeneration(generation)"
            >
              <span>{{ generation.style_key }}</span>
              <strong>{{ generation.status }}</strong>
            </button>
            <p v-if="!diaryGenerations.length && !diaryLoading" class="empty-state">这个日期还没有生成记录。</p>
          </article>
        </div>
      </section>
    </section>

    <section v-else-if="activeView === 'story'" class="workspace">
      <header class="page-header">
        <p class="eyebrow">Story</p>
        <h2>故事详情</h2>
      </header>
      <section class="panel story-panel">
        <div class="tab-row">
          <button
            v-for="tab in polishTabs"
            :key="tab.key"
            :class="{ active: activeStoryTab === tab.key }"
            type="button"
            @click="switchStoryTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
        <p v-if="storyLoading" class="status-text">AI 润色中...</p>
        <article class="story-text">{{ storyText }}</article>
        <label for="story-edit">编辑后的提示词</label>
        <textarea id="story-edit" v-model="editedStoryText" class="edit-area"></textarea>
        <div class="button-row">
          <button type="button" @click="saveEditedStory">保存编辑</button>
          <button type="button" @click="extractEmotion">提取情绪标签</button>
        </div>
        <dl v-if="emotion" class="emotion-grid">
          <div v-for="(value, key) in emotion" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </div>
        </dl>
      </section>
    </section>

    <section v-else class="workspace">
      <header class="page-header">
        <p class="eyebrow">Collection</p>
        <h2>最近 30 天故事集</h2>
      </header>
      <section class="story-collection">
        <p v-if="collectionLoading" class="status-text">加载中...</p>
        <article v-for="group in storyGroups" :key="group.date" class="story-card">
          <span>{{ group.date }}</span>
          <h3>{{ group.memories.length }} 条记忆</h3>
          <p>{{ group.memories[0]?.content_text || '图片记忆' }}</p>
        </article>
        <p v-if="!storyGroups.length && !collectionLoading" class="empty-state">最近 30 天还没有可展示的故事。</p>
      </section>
    </section>
  </main>
</template>
