<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import {
  ActionSheet,
  showToast,
  showSuccessToast,
  showFailToast,
  showLoadingToast,
  Icon,
} from 'vant'
import { polishText } from '../api'

const router = useRouter()
const store = useAppStore()

const fileList = ref([])
const memoryText = ref('')
const showStyleSheet = ref(false)
const isExpanded = ref(false)
const selectedStyle = ref('default')
const styleName = ref('风格')
const isPolishing = ref(false)
const isConfirmed = ref(false)
const savedMemoryId = ref(null)

const styleOptions = [
  { name: '默认风格', value: 'default' },
  { name: '温暖治愈', value: 'warm' },
  { name: '高冷文艺', value: 'cool' },
  { name: '幽默风趣', value: 'humor' },
  { name: '戏剧张力', value: 'dramatic' },
]

const canPolish = computed(() => memoryText.value.trim().length > 0)
const canConfirm = computed(() => fileList.value.length > 0 || memoryText.value.trim().length > 0)

function onStyleSelect(option) {
  selectedStyle.value = option.value
  styleName.value = option.name
  showStyleSheet.value = false
}

function onUploadClick() {
  document.getElementById('file-upload')?.click()
}

function handleFileChange(e) {
  const files = Array.from(e.target.files || [])
  files.forEach(file => {
    const isImage = file.type.startsWith('image/')
    if (isImage) {
      const reader = new FileReader()
      reader.onload = (event) => {
        fileList.value.push({
          file,
          type: 'image',
          preview: event.target.result,
          name: file.name,
        })
        showSuccessToast('图片已选择')
      }
      reader.readAsDataURL(file)
    }
  })
  e.target.value = ''
}

function onMemoryClick() {
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    // wait for DOM update then focus
    setTimeout(() => {
      document.getElementById('memory-textarea')?.focus()
    }, 100)
  }
}

async function handlePolish() {
  if (!canPolish.value) {
    showToast('请先输入回忆内容')
    return
  }

  isPolishing.value = true
  try {
    const result = await polishText({
      text: memoryText.value.trim(),
      style_key: 'polished'
    })
    memoryText.value = result.polished_text
    showSuccessToast('润色完成')
  } catch (error) {
    showFailToast(error.message || '润色失败')
    console.error(error)
  } finally {
    isPolishing.value = false
  }
}

async function handleConfirm() {
  if (!canConfirm.value) {
    showToast('请先上传图片或输入回忆内容')
    return
  }

  try {
    showLoadingToast({ message: '保存记录中...', forbidClick: true })
    const memory = await store.saveMemory(memoryText.value.trim(), fileList.value.map(f => f.file))
    savedMemoryId.value = memory.id
    isConfirmed.value = true
    showSuccessToast('已确认保存')
  } catch (error) {
    showFailToast(error.message || '保存失败')
    console.error(error)
  }
}

async function startGeneration() {
  if (!isConfirmed.value) {
    showToast('请先点击确认保存')
    return
  }

  try {
    showLoadingToast({ message: 'AI漫画生成中...', forbidClick: true })
    const data = await store.generateStory(selectedStyle.value)
    showSuccessToast('生成完成')
    router.push(`/story/${data.generation_id}`)
  } catch (error) {
    showFailToast(error.message || '生成失败')
    console.error(error)
  }
}
</script>

<template>
  <div class="page-container home-page">
    <!-- 顶部用户信息 -->
    <div class="header">
      <div class="user-pill">
        <Icon name="user-circle-o" class="user-icon" />
        <span class="user-name">悲伤的企鹅</span>
        <Icon name="arrow-down" class="arrow-icon" />
      </div>
    </div>

    <!-- Logo区域 -->
    <div class="logo-section">
      <div class="logo-z">
        <svg viewBox="0 0 24 24" width="64" height="64">
          <path d="M4 4h16v2L6 20h14v2H2v-2L18 6H4V4z" fill="currentColor"/>
        </svg>
      </div>
      <p class="slogan">你的生活不是流水账</p>
      <p class="slogan-sub">而是一部未完待续的英雄传记</p>
    </div>

    <!-- 操作卡片区 -->
    <div class="action-cards">
      <!-- 上传图片 -->
      <div class="action-card white-card" @click="onUploadClick">
        <div class="card-content">
          <h3>上传图片</h3>
          <p>把平凡的流水账，拍成热血的名场面</p>
          <span v-if="fileList.length > 0" class="file-count">已选 {{ fileList.length }} 张</span>
        </div>
        <div class="card-icon-wrapper" :class="{ 'has-images': fileList.length > 0 }">
          <Icon v-if="fileList.length === 0" name="photo" class="card-icon" />
          <div v-else class="image-stack">
            <img 
              v-for="(file, index) in fileList.slice(0, 3)" 
              :key="index"
              :src="file.preview"
              class="stack-img"
            />
            <div class="add-more-btn">
              <Icon name="plus" />
            </div>
          </div>
        </div>
      </div>
      
      <input
        id="file-upload"
        type="file"
        accept="image/*"
        multiple
        hidden
        @change="handleFileChange"
      />

      <!-- 开始回忆 -->
      <div class="action-card beige-card" :class="{ 'expanded': isExpanded }" @click.self="isExpanded = true">
        <div class="card-content" @click="onMemoryClick">
          <h3>开始回忆</h3>
          <p v-if="!isExpanded">每一段小确幸，都值得被全世界震惊</p>
        </div>
        <div class="card-icon-wrapper dark-bg" v-if="!isExpanded" @click="onMemoryClick">
          <Icon name="edit" class="card-icon white-icon" />
        </div>
        
        <div class="expanded-content" v-show="isExpanded">
          <textarea
            id="memory-textarea"
            v-model="memoryText"
            rows="4"
            placeholder="今天发生了什么有趣的事情..."
            class="inline-textarea"
          ></textarea>
          <div class="action-buttons" v-if="isExpanded">
            <button
              class="action-btn polish-btn"
              :disabled="!canPolish || isPolishing"
              @click.stop="handlePolish"
            >
              <Icon name="brush-o" class="btn-icon" />
              {{ isPolishing ? '润色中...' : 'AI润色' }}
            </button>
            <button
              class="action-btn confirm-btn"
              :class="{ 'confirmed': isConfirmed }"
              :disabled="!canConfirm || isConfirmed"
              @click.stop="handleConfirm"
            >
              <Icon :name="isConfirmed ? 'success' : 'passed'" class="btn-icon" />
              {{ isConfirmed ? '已确认' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作区 -->
    <div class="bottom-actions">
      <div class="style-selector" @click="showStyleSheet = true">
        <span>{{ styleName }}</span>
        <Icon name="arrow-down" />
      </div>

      <button
        class="generate-btn"
        :class="{ 'disabled': !isConfirmed }"
        :disabled="!isConfirmed"
        @click="startGeneration"
      >
        <Icon name="play-circle-o" class="btn-icon" />
        漫画人生
      </button>
    </div>

    <!-- 风格选择弹窗 -->
    <ActionSheet
      v-model:show="showStyleSheet"
      title="选择风格"
      :actions="styleOptions.map(o => ({ name: o.name, value: o.value }))"
      @select="onStyleSelect"
    />
  </div>
</template>

<style scoped>
.home-page {
  padding: 20px 24px 100px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  margin-bottom: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(0,0,0,0.03);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-color);
}

.user-icon {
  font-size: 16px;
}

.arrow-icon {
  font-size: 12px;
  color: var(--light-text);
}

.logo-section {
  text-align: center;
  margin-bottom: 48px;
}

.logo-z {
  color: var(--text-color);
  margin-bottom: 24px;
}

.slogan {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 8px;
  letter-spacing: 2px;
}

.slogan-sub {
  font-size: 14px;
  color: #888;
  letter-spacing: 1px;
}

.action-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 40px;
}

.action-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.action-card:not(.expanded):active {
  transform: scale(0.98);
}

.white-card {
  background: #FFFFFF;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.03);
}

.beige-card {
  background: #F4EDE4;
  border: 1px solid rgba(0,0,0,0.02);
  flex-direction: row;
  flex-wrap: wrap;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.02);
}

.beige-card.expanded {
  flex-direction: column;
  align-items: flex-start;
  padding-bottom: 20px;
}

.beige-card.expanded .card-content {
  width: 100%;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.expanded-content {
  width: 100%;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.inline-textarea {
  width: 100%;
  border: none;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  padding: 16px;
  font-size: 15px;
  color: var(--text-color);
  resize: none;
  outline: none;
  transition: background 0.2s;
}

.inline-textarea:focus {
  background: rgba(255, 255, 255, 0.8);
}

.inline-textarea::placeholder {
  color: #a8a096;
}

.card-content h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-color);
}

.card-content p {
  font-size: 13px;
  color: var(--light-text);
  line-height: 1.5;
  max-width: 180px;
}

.memory-preview {
  color: var(--primary-color) !important;
  font-weight: 500;
}

.file-count {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--primary-color);
  background: rgba(92, 62, 50, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.card-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F5F6F8;
}

.card-icon-wrapper.has-images {
  background: transparent;
}

.image-stack {
  position: relative;
  width: 100%;
  height: 100%;
}

.stack-img {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  top: 0;
  left: 0;
  transition: all 0.3s;
}

.stack-img:nth-child(1) {
  transform: rotate(-8deg);
  z-index: 1;
}

.stack-img:nth-child(2) {
  transform: rotate(6deg);
  z-index: 2;
}

.stack-img:nth-child(3) {
  transform: rotate(-2deg);
  z-index: 3;
}

.add-more-btn {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 24px;
  height: 24px;
  background: #4A4A4A;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 4;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  font-size: 14px;
}

.card-icon-wrapper.dark-bg {
  background: #4A4A4A;
}

.card-icon {
  font-size: 28px;
  color: #666;
}

.white-icon {
  color: #FFF;
}

.bottom-actions {
  margin-top: auto;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 20px;
}

.style-selector {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 20px;
  height: 56px;
  background: #FFFFFF;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 28px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
}

.style-selector:active {
  transform: scale(0.96);
}

.generate-btn {
  flex: 1;
  background: var(--primary-color);
  color: white;
  font-size: 18px;
  font-weight: 600;
  height: 56px;
  padding: 0;
  border-radius: 28px;
  border: none;
  box-shadow: 0 8px 20px rgba(92, 62, 50, 0.25);
  cursor: pointer;
  transition: transform 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.generate-btn:active {
  transform: scale(0.96);
}

.btn-icon {
  font-size: 20px;
  margin-right: 4px;
}

.text-input-dialog {
  padding: 16px;
}

.custom-textarea {
  width: 100%;
  border: none;
  background: #F5F6F8;
  border-radius: 12px;
  padding: 16px;
  font-size: 15px;
  color: var(--text-color);
  resize: none;
  outline: none;
}

.custom-textarea::placeholder {
  color: #bbb;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 16px;
  border-radius: 16px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn:active:not(:disabled) {
  transform: scale(0.96);
}

.polish-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.polish-btn:disabled {
  background: #ccc;
  box-shadow: none;
}

.confirm-btn {
  background: #FFFFFF;
  color: var(--text-color);
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.confirm-btn.confirmed {
  background: #52c41a;
  color: white;
  border-color: #52c41a;
}

.generate-btn.disabled {
  background: #ccc;
  box-shadow: none;
  cursor: not-allowed;
}
</style>
