<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Icon, Swipe, SwipeItem, showLoadingToast, showSuccessToast, showFailToast, closeToast, Dialog, Field } from 'vant'
import { useAppStore } from '../stores/app'
import { polishDiary, updatePrompt, STYLE_NAMES } from '../api'

const router = useRouter()
const route = useRoute()
const store = useAppStore()

// Mock data as fallback
const storyData = ref({
  title: '生成记录',
  images: ['https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'],
  content: '加载中...',
  likes: 0,
  stars: 0,
  comments: 0
})

const activeTab = ref('polished')
const generationId = ref(null)
const rawDiary = ref('')
const isEditing = ref(false)
const editContent = ref('')
const currentImageIndex = ref(0)

const imageCount = computed(() => storyData.value.images.length)

const tabs = [
  { key: 'original', label: '原文' },
  { key: 'polished', label: '润色稿' },
  { key: 'wechat', label: '朋友圈' },
  { key: 'xiaohongshu', label: '小红书' },
]

async function loadData() {
  try {
    const genId = route.params.id
    if (!genId) return
    generationId.value = genId
    
    const api = await import('../api')
    const gen = await api.getGeneration(genId)
    const details = await store.loadGenerationDetails(gen)
    
    // Update storyData
    storyData.value.title = STYLE_NAMES[gen.style_key] || gen.style_key || '生成记录'

    // Collect all images for carousel
    const images = []
    if (details.media && details.media.length > 0) {
      details.media.forEach(m => {
        images.push(`/uploads/${m.file_path}`)
      })
    }
    if (details.output) {
      const fileName = details.output.file_path ? details.output.file_path.replace(/\\/g, '/').split('/').pop() : details.output.url?.split('/').pop()
      images.unshift(`/outputs/${gen.id}/${fileName}`)
    }
    if (images.length === 0) {
      images.push('https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg')
    }
    storyData.value.images = images

    // Get diary text - primary source is user_edited_prompt (LLM generated diary)
    let diaryText = gen.user_edited_prompt || ''

    // Fallback: try to extract from vlm_raw_metadata if user_edited_prompt is empty
    if (!diaryText && gen.vlm_raw_metadata) {
      const meta = typeof gen.vlm_raw_metadata === 'string'
        ? JSON.parse(gen.vlm_raw_metadata)
        : gen.vlm_raw_metadata

      if (meta && typeof meta === 'object') {
        if (meta.diary) {
          diaryText = meta.diary
        } else if (Array.isArray(meta)) {
          // Scene array - create summary
          diaryText = meta.map(scene => {
            const parts = []
            if (scene.scene) parts.push(scene.scene)
            if (scene.people) parts.push(scene.people)
            return parts.join('，')
          }).join('\n\n')
        }
      }
    }
    rawDiary.value = diaryText

    // Set content based on priority: polished > original diary
    if (gen.llm_polished_prompt) {
      storyData.value.content = gen.llm_polished_prompt
      activeTab.value = 'polished'
    } else if (diaryText) {
      storyData.value.content = diaryText
      activeTab.value = 'original'
    }
  } catch (error) {
    console.error(error)
  }
}

async function switchTab(tabKey) {
  if (activeTab.value === tabKey) return
  activeTab.value = tabKey
  
  if (tabKey === 'original') {
    storyData.value.content = rawDiary.value
    return
  }
  
  const polishStyleMap = {
    polished: 'polished',
    wechat: 'moments',
    xiaohongshu: 'xiaohongshu'
  }
  
  const style = polishStyleMap[tabKey]
  if (!style || !generationId.value) return
  
  try {
    showLoadingToast({ message: 'AI润色中...', forbidClick: true })
    const result = await polishDiary(generationId.value, {
      diary_text: rawDiary.value,
      style_key: style
    })
    storyData.value.content = result.polished_text
    closeToast()
  } catch (error) {
    showFailToast('润色失败')
    console.error(error)
  }
}

async function saveContent() {
  if (!generationId.value) return
  try {
    await updatePrompt(generationId.value, {
      user_edited_prompt: storyData.value.content
    })
    showSuccessToast('保存成功')
  } catch (error) {
    console.error(error)
    showFailToast('保存失败')
  }
}

function startEditing() {
  editContent.value = storyData.value.content
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  editContent.value = ''
}

async function saveEditing() {
  storyData.value.content = editContent.value
  isEditing.value = false
  await saveContent()
}

function onSwipeChange(index) {
  currentImageIndex.value = index
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="story-page">
    <!-- 图片轮播层 -->
    <div class="image-layer">
      <Swipe :autoplay="5000" :show-indicators="false" class="story-swiper" @change="onSwipeChange">
        <SwipeItem v-for="(img, index) in storyData.images" :key="index">
          <img :src="img" alt="故事图片" class="bg-image" />
        </SwipeItem>
      </Swipe>

      <!-- 顶部导航悬浮在图片上 -->
      <div class="nav-header">
        <div class="nav-back" @click="router.back()">
          <Icon name="arrow-left" />
        </div>
        <div class="nav-right">
          <div class="image-counter" v-if="imageCount > 1">
            {{ currentImageIndex + 1 }}/{{ imageCount }}
          </div>
        </div>
      </div>
    </div>

    <!-- 内容卡片层 -->
    <div class="content-layer">
      <!-- 拖拽指示器 -->
      <div class="drag-indicator"></div>

      <!-- 标题 -->
      <h1 class="story-title">{{ storyData.title }}</h1>

      <!-- Tabs -->
      <div class="tabs-scroll">
        <div class="pill-tabs">
          <div
            v-for="tab in tabs"
            :key="tab.key"
            class="pill-tab"
            :class="{ active: activeTab === tab.key }"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </div>
        </div>
      </div>

      <!-- 额外信息 -->
      <div class="extra-info">
      </div>

      <!-- 文本内容区域 -->
      <div class="story-text-container">
        <!-- 查看模式 -->
        <div v-if="!isEditing" class="text-view-mode">
          <div class="story-text-content">{{ storyData.content }}</div>
          <button class="edit-trigger" @click="startEditing">
            <Icon name="edit" />
            <span>编辑</span>
          </button>
        </div>

        <!-- 编辑模式 -->
        <div v-else class="text-edit-mode">
          <Field
            v-model="editContent"
            type="textarea"
            autosize
            :border="false"
            placeholder="在这里编辑您的日记内容..."
            class="custom-textarea editing"
            autofocus
          />
          <div class="edit-actions">
            <button class="action-btn cancel" @click="cancelEditing">取消</button>
            <button class="action-btn save" @click="saveEditing">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.story-page {
  min-height: 100vh;
  min-height: 100dvh;
  background: #EBEBE6;
  position: relative;
  /* PC端居中限制宽度 */
  max-width: 600px;
  margin: 0 auto;
  box-shadow: 0 0 20px rgba(0,0,0,0.05);
}

.image-layer {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 65vh;
  height: 65dvh;
  z-index: 0;
  /* 确保背景层在PC端也能与内容对齐 */
  display: flex;
  justify-content: center;
}

.bg-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  /* PC端图片也限制最大宽度 */
  max-width: 600px;
}

.nav-header {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 600px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  /* 适配刘海屏 */
  padding-top: calc(16px + env(safe-area-inset-top));
  background: transparent;
  z-index: 10;
}

.nav-back {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #333;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  backdrop-filter: blur(4px);
  cursor: pointer;
}

.nav-right {
  width: 32px;
}

.content-layer {
  position: relative;
  box-sizing: border-box;
  margin-top: 50vh;
  margin-top: 50dvh; /* 卡片距离顶部的位置 */
  min-height: 50vh;
  min-height: 50dvh;
  z-index: 1;
  padding: 24px 20px calc(40px + env(safe-area-inset-bottom));
  border-radius: 40px 40px 0 0;
  background: linear-gradient(to bottom, rgba(235, 235, 230, 0.6) 0%, rgba(235, 235, 230, 0.95) 150px, #EBEBE6 300px);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.drag-indicator {
  width: 36px;
  height: 4px;
  background: rgba(255, 255, 255, 1);
  border-radius: 2px;
  margin: 0 auto 24px;
}

.story-title {
  font-size: clamp(20px, 6vw, 26px);
  font-weight: 600;
  color: #333;
  text-align: center;
  margin: 0 0 32px 0;
  letter-spacing: 1px;
}

.tabs-scroll {
  overflow-x: auto;
  margin: 0 -20px 24px;
  padding: 0 20px;
  scrollbar-width: none;
}

.tabs-scroll::-webkit-scrollbar {
  display: none;
}

.pill-tabs {
  display: flex;
  gap: 10px;
  width: max-content;
  margin: 0 auto;
}

.pill-tab {
  padding: 8px 20px;
  border-radius: 24px;
  font-size: 14px;
  color: #666;
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
}

.pill-tab.active {
  background: #333;
  color: white;
  font-weight: 500;
}

.extra-info {
  font-size: clamp(14px, 4vw, 16px);
  color: #333;
  margin-bottom: 24px;
  padding: 0 4px;
  font-weight: 500;
}

.cost-icon {
  margin-right: 4px;
}

.story-text-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  padding: 20px 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
}

.custom-textarea {
  padding: 0;
  background: transparent;
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}

.custom-textarea :deep(.van-field__control) {
  color: #333;
  text-align: justify;
}

/* 图片轮播样式 */
.story-swiper {
  width: 100%;
  height: 100%;
}

.story-swiper :deep(.van-swipe-item) {
  overflow: hidden;
}

.image-counter {
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  backdrop-filter: blur(4px);
}

/* 文本查看模式 */
.text-view-mode {
  position: relative;
}

.story-text-content {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.edit-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 16px;
  padding: 8px 16px;
  background: #f5f5f5;
  border: none;
  border-radius: 20px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-trigger:active {
  background: #eee;
  transform: scale(0.96);
}

/* 文本编辑模式 */
.text-edit-mode {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.custom-textarea.editing {
  background: #f9f9f9;
  border-radius: 12px;
  padding: 12px;
}

.edit-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.action-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.cancel {
  background: #f0f0f0;
  color: #666;
}

.action-btn.cancel:active {
  background: #e5e5e5;
}

.action-btn.save {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.action-btn.save:active {
  transform: scale(0.96);
}
</style>
