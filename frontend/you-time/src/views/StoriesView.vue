<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listMemories, getMemoryMedia } from '../api'
import {
  NavBar,
  CellGroup,
  Cell,
  Icon,
} from 'vant'

const router = useRouter()

const groupedMemories = ref({})

function formatGroupDate(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parseInt(parts[1])}月${parseInt(parts[2])}日`
}

async function loadStories() {
  try {
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

    const result = await listMemories({
      start_date: startDate,
      end_date: endDate,
      limit: 100,
    })

    // 按日期分组
    const grouped = {}
    for (const memory of result.memories || []) {
      const date = memory.memory_date
      if (!grouped[date]) grouped[date] = []
      grouped[date].push(memory)
    }

    groupedMemories.value = grouped
  } catch (error) {
    console.error('加载故事集失败:', error)
  }
}

function viewGroup(date) {
  router.push({
    path: '/diary',
    query: { date },
  })
}

onMounted(loadStories)
</script>

<template>
  <div class="page-container stories-page">
    <!-- 顶部导航 -->
    <div class="nav-header">
      <div class="nav-left"></div>
      <div class="nav-right">
        <Icon name="plus" class="nav-icon" @click="router.push('/home')" />
      </div>
    </div>

    <!-- 列表标题 -->
    <div class="section-header">
      <h2 class="section-title">故事集</h2>
      <span class="section-count" v-if="Object.keys(groupedMemories).length > 0">共{{ Object.keys(groupedMemories).length }}天</span>
    </div>

    <!-- 故事列表 -->
    <div v-if="Object.keys(groupedMemories).length > 0" class="comic-list">
      <div
        v-for="(group, date) in groupedMemories"
        :key="date"
        class="comic-card"
        @click="viewGroup(date)"
      >
        <div class="comic-cover">
          <Icon name="notes-o" class="cover-icon" />
        </div>
        <div class="comic-info">
          <h3>{{ formatGroupDate(date) }}的记忆</h3>
          <p class="comic-preview">收录了这天的 {{ group.length }} 个故事片段</p>
          <div class="comic-meta">
            <span class="comic-date">{{ date }}</span>
            <div class="comic-tags">
              <span class="comic-tag">
                <Icon name="photo-o" /> {{ group.length }} 记录
              </span>
            </div>
          </div>
        </div>
        <Icon name="arrow" class="card-arrow" />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <Icon name="records" size="48" />
      <p>暂无故事集</p>
      <p class="empty-hint">去首页记录你的第一个故事吧</p>
    </div>
  </div>
</template>

<style scoped>
.stories-page {
  padding: 16px 20px;
  padding-bottom: 100px;
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0 24px;
}

.nav-left {
  width: 24px; /* balance the flex space */
}

.nav-icon {
  font-size: 24px;
  color: var(--text-color);
  cursor: pointer;
}

.nav-right {
  display: flex;
  gap: 16px;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--light-text);
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

.comic-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comic-card {
  display: flex;
  align-items: center;
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
  width: 80px;
  height: 80px;
  border-radius: 14px;
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
  background: #f5f6f8;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-icon {
  font-size: 32px;
  color: #ccc;
}

.comic-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1;
  min-width: 0;
}

.comic-info h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comic-preview {
  font-size: 13px;
  color: #888;
  line-height: 1.5;
  margin-bottom: 8px;
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

.card-arrow {
  color: #ccc;
  font-size: 16px;
  margin-right: 4px;
}
</style>
