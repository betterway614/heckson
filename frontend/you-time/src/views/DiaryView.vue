<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { Icon, showFailToast, showLoadingToast, showSuccessToast, closeToast } from 'vant'
import { createDailyDiary, streamGenerationProgress, STYLE_NAMES } from '../api'
import { getMonthGrid, isSameMonth, formatMonthTitle, shiftMonth, toMonthStart } from '../utils/calendar'

const router = useRouter()
const route = useRoute()
const store = useAppStore()

const calendarDate = ref(new Date()) // Used for calendar display (month/year)
const selectedDate = ref(null) // Used for filtering, null means show all
const generations = ref([])
const totalCount = ref(0)
const daysInMonth = ref([])
const daysWithData = ref([])
const weekDays = ['SM', 'M', 'T', 'W', 'T', 'F', 'S']
const loading = ref(false)
const generating = ref(false)
const generateProgress = ref(0)
const touchStart = ref(null)

const calendarTitle = computed(() => formatMonthTitle(calendarDate.value))

function formatDate(date) {
  if (!date) return null
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatDisplayDate(dateStr) {
  const d = new Date(dateStr)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

function generateCalendar() {
  calendarDate.value = toMonthStart(calendarDate.value)
  daysInMonth.value = getMonthGrid(calendarDate.value)
}

async function loadMonthData() {
  try {
    const year = calendarDate.value.getFullYear()
    const month = calendarDate.value.getMonth()
    daysWithData.value = await store.loadMonthDates(year, month)
  } catch (error) {
    console.error('加载月度数据失败:', error)
  }
}

function isDaySelected(day) {
  if (!day || !selectedDate.value) return false
  if (!isSameMonth(selectedDate.value, calendarDate.value)) return false
  return day === selectedDate.value.getDate()
}

function changeMonth(delta) {
  const hadSelection = !!selectedDate.value
  selectedDate.value = null
  calendarDate.value = shiftMonth(calendarDate.value, delta)
  generateCalendar()
  loadMonthData()
  if (hadSelection) loadData()
}

function prevMonth() {
  changeMonth(-1)
}

function nextMonth() {
  changeMonth(1)
}

function onCalendarTouchStart(e) {
  const touch = e.touches?.[0]
  if (!touch) return
  touchStart.value = { x: touch.clientX, y: touch.clientY }
}

function onCalendarTouchEnd(e) {
  const start = touchStart.value
  touchStart.value = null
  if (!start) return
  const touch = e.changedTouches?.[0]
  if (!touch) return

  const dx = touch.clientX - start.x
  const dy = touch.clientY - start.y
  if (Math.abs(dx) < 50) return
  if (Math.abs(dx) < Math.abs(dy)) return

  if (dx > 0) prevMonth()
  else nextMonth()
}

async function loadData() {
  loading.value = true
  try {
    const dateStr = formatDate(selectedDate.value)
    const data = await store.loadDayData(dateStr || undefined)

    generations.value = data.generations.map(gen => {
      // Find original image from memory
      let originalImage = null;
      if (gen.memory_ids && gen.memory_ids.length > 0) {
        const genMedia = data.media.find(m => gen.memory_ids.includes(m.memory_id));
        if (genMedia) {
          originalImage = `/uploads/${genMedia.file_path}`;
        }
      } else if (data.media && data.media.length > 0) {
        originalImage = `/uploads/${data.media[0].file_path}`;
      }

      // Find output image (一日图)
      let outputImage = null;
      if (gen.outputs && gen.outputs.length > 0) {
        const output = gen.outputs[0]
        const fileName = output.file_path ? output.file_path.split('/').pop() : output.url?.split('/').pop()
        if (fileName) {
          outputImage = `/outputs/${gen.id}/${fileName}`
        }
      }

      // Extract diary text content - primary source is user_edited_prompt
      let title = STYLE_NAMES[gen.style_key] || gen.style_key || '生成记录';
      let textContent = gen.user_edited_prompt || '';
      let previewText = '';

      // Fallback: try to extract from vlm_raw_metadata
      if (!textContent && gen.vlm_raw_metadata) {
        let meta = gen.vlm_raw_metadata;
        if (typeof meta === 'string') {
          try { meta = JSON.parse(meta); } catch(e){}
        }

        if (meta && typeof meta === 'object') {
          if (meta.diary) {
            textContent = meta.diary
          } else if (Array.isArray(meta)) {
            // Scene array - extract summary
            textContent = meta.map(scene => {
              const parts = []
              if (scene.scene) parts.push(scene.scene)
              if (scene.people) parts.push(scene.people)
              return parts.join('，')
            }).join('；')
          }
          if (meta.title) title = meta.title;
        }
      }

      // Use polished prompt if available (highest priority)
      if (gen.llm_polished_prompt) {
        textContent = gen.llm_polished_prompt;
      }

      // Generate preview text (first line or first 30 chars)
      if (textContent) {
        previewText = textContent.split(/[\n。！？!?；;]/)[0].slice(0, 30)
        if (textContent.length > 30) previewText += '...'
      }

      // Auto-generate title from content if not set
      if ((title === '生成记录' || title === STYLE_NAMES[gen.style_key] || title === gen.style_key) && previewText) {
        title = previewText.slice(0, 15)
      }

      return {
        id: gen.id,
        title: title,
        previewText: previewText || '暂无内容',
        date: formatDisplayDate(gen.created_at || new Date()),
        image: originalImage || 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg',
        outputImage: outputImage,
        hasOriginal: !!originalImage,
        hasOutput: !!outputImage,
        type: gen.type || 'diary'
      }
    })
    totalCount.value = generations.value.length
  } catch (error) {
    console.error('加载数据失败:', error)
    showFailToast('加载失败，请重试')
  } finally {
    loading.value = false
  }
}

function selectDate(day) {
  if (!day) return
  const newSelectedDate = new Date(calendarDate.value.getFullYear(), calendarDate.value.getMonth(), day)
  
  // Toggle selection: if clicking the already selected date, unselect it to show all
  if (selectedDate.value && selectedDate.value.getTime() === newSelectedDate.getTime()) {
    selectedDate.value = null
  } else {
    selectedDate.value = newSelectedDate
  }
  
  loadData()
}

function viewGeneration(gen) {
  router.push(`/story/${gen.id}`)
}

async function generateDailyDiary() {
  if (generating.value) return

  const targetDate = formatDate(selectedDate.value) || formatDate(new Date())

  generating.value = true
  generateProgress.value = 0
  showLoadingToast({ message: '正在生成一日漫画...', forbidClick: true })

  try {
    const generation = await createDailyDiary(targetDate)

    // 监听进度
    streamGenerationProgress(generation.id, {
      onProgress: (data) => {
        generateProgress.value = data.progress || 0
      },
      onComplete: (data) => {
        generating.value = false
        closeToast()
        showSuccessToast('一日漫画生成完成')
        // 跳转到详情页
        router.push(`/story/${data.generation_id}`)
      },
      onError: () => {
        generating.value = false
        closeToast()
        showFailToast('生成失败，请重试')
      }
    })
  } catch (error) {
    generating.value = false
    closeToast()
    showFailToast(error.message || '生成失败')
  }
}

onMounted(() => {
  if (route.query.date) {
    selectedDate.value = new Date(route.query.date)
    calendarDate.value = new Date(route.query.date)
  }
  generateCalendar()
  loadMonthData()
  loadData()
})

watch(() => route.query.date, (newDate) => {
  if (newDate) {
    selectedDate.value = new Date(newDate)
    calendarDate.value = new Date(newDate)
  } else {
    selectedDate.value = null
  }
  generateCalendar()
  loadMonthData()
  loadData()
})
</script>

<template>
  <div class="page-container diary-page">
    <!-- 顶部导航 -->
    <div class="nav-header">
      <Icon name="arrow-left" class="nav-icon" @click="router.back()" />
      <div class="nav-right">
        <Icon name="search" class="nav-icon" />
        <Icon name="plus" class="nav-icon" />
      </div>
    </div>

    <!-- 日历卡片 -->
    <div class="calendar-card">
      <div class="month-header">
        <button class="month-btn" type="button" @click="prevMonth">
          <Icon name="arrow-left" />
        </button>
        <div class="month-title">{{ calendarTitle }}</div>
        <button class="month-btn" type="button" @click="nextMonth">
          <Icon name="arrow" />
        </button>
      </div>
      <div class="week-header">
        <span v-for="day in weekDays" :key="day">{{ day }}</span>
      </div>
      <div class="days-grid" @touchstart="onCalendarTouchStart" @touchend="onCalendarTouchEnd">
        <div 
          v-for="(day, index) in daysInMonth" 
          :key="index"
          class="day-cell"
          :class="{ 
            'is-selected': isDaySelected(day),
            'has-data': day && daysWithData.includes(day)
          }"
          @click="selectDate(day)"
        >
          {{ day }}
        </div>
      </div>
    </div>

    <!-- 列表标题 -->
    <div class="section-header">
      <h2 class="section-title">人生漫画册</h2>
      <span class="section-count">共{{ totalCount }}篇</span>
    </div>

    <!-- 一键生成一日漫画按钮 -->
    <div class="daily-diary-action">
      <button
        class="daily-diary-btn"
        :class="{ generating: generating }"
        :disabled="generating"
        @click="generateDailyDiary"
      >
        <Icon v-if="!generating" name="brush-o" />
        <div v-else class="btn-spinner"></div>
        <span>{{ generating ? `生成中 ${generateProgress}%` : '生成今日漫画' }}</span>
      </button>
      <p class="daily-diary-hint">汇总当天所有记忆，一键生成生活漫画</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="generations.length === 0" class="empty-state">
      <Icon name="photo-o" size="48" />
      <p>暂无生成记录</p>
      <p class="empty-hint">去首页添加事件，生成你的一日漫画吧</p>
    </div>

    <!-- 日记列表 -->
    <div v-else class="comic-list">
      <div
        v-for="gen in generations"
        :key="gen.id"
        class="comic-card"
        @click="viewGeneration(gen)"
      >
        <div class="comic-cover">
          <img :src="gen.outputImage || gen.image" :alt="gen.title" />
          <div v-if="gen.hasOutput" class="cover-badge">一日图</div>
        </div>
        <div class="comic-info">
          <h3>{{ gen.title }}</h3>
          <p class="comic-preview">{{ gen.previewText }}</p>
          <div class="comic-meta">
            <span class="comic-date">{{ gen.date }}</span>
            <div class="comic-tags">
              <span v-if="gen.hasOriginal" class="comic-tag">
                <Icon name="photo-o" /> 原图
              </span>
              <span v-if="gen.hasOutput" class="comic-tag output-tag">
                <Icon name="image-o" /> 一日图
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diary-page {
  padding: 16px 20px;
  padding-bottom: 100px;
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0 24px;
}

.nav-icon {
  font-size: 24px;
  color: var(--text-color);
}

.nav-right {
  display: flex;
  gap: 16px;
}

.calendar-card {
  background: white;
  border-radius: 24px;
  padding: 24px 20px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.03);
  margin-bottom: 32px;
}

.month-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.month-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
}

.month-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f6f6f6;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-color);
  cursor: pointer;
}

.month-btn:active {
  transform: scale(0.95);
}

.week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  margin-bottom: 16px;
  font-size: 12px;
  color: #ccc;
}

.days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  row-gap: 16px;
  text-align: center;
}

.day-cell {
  font-size: 15px;
  color: var(--text-color);
  height: 32px;
  width: 32px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  position: relative;
}

.day-cell.has-data::after {
  content: '';
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: #ff9800;
}

.day-cell.is-selected {
  font-weight: bold;
  background-color: var(--text-color);
  color: white;
}

.day-cell.is-selected.has-data::after {
  background-color: white;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
  padding: 0 4px;
}

.section-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-color);
}

.section-count {
  font-size: 13px;
  color: var(--light-text);
}

/* Loading and Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--light-text);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid var(--text-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state p {
  margin-top: 16px;
  font-size: 16px;
}

.empty-hint {
  font-size: 13px !important;
  color: #ccc;
  margin-top: 8px !important;
}

/* List Styles */
.comic-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comic-card {
  display: flex;
  background: white;
  border-radius: 20px;
  padding: 12px;
  gap: 14px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.comic-card:active {
  transform: scale(0.98);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.comic-cover {
  width: 100px;
  height: 80px;
  border-radius: 14px;
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
}

.comic-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-badge {
  position: absolute;
  bottom: 6px;
  left: 6px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  backdrop-filter: blur(4px);
}

.comic-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1;
  min-width: 0;
}

.comic-info h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comic-preview {
  font-size: 12px;
  color: #888;
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.comic-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.comic-date {
  font-size: 11px;
  color: #bbb;
}

.comic-tags {
  display: flex;
  gap: 6px;
}

.comic-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  color: var(--light-text);
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.output-tag {
  background: #e8f4fd;
  color: #4a9eff;
}

/* 一日漫画生成按钮 */
.daily-diary-action {
  margin-bottom: 20px;
  text-align: center;
}

.daily-diary-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border: none;
  border-radius: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.daily-diary-btn:active:not(:disabled) {
  transform: scale(0.96);
}

.daily-diary-btn:disabled {
  opacity: 0.8;
  cursor: not-allowed;
}

.daily-diary-btn.generating {
  background: linear-gradient(135deg, #a8a8a8 0%, #888 100%);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.daily-diary-hint {
  font-size: 12px;
  color: #bbb;
  margin-top: 8px;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
