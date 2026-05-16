import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  createMemory,
  listMemories,
  getMemory,
  getMemoryMedia,
  uploadMedia,
  createGeneration,
  getGeneration,
  listGenerations,
  getGenerationOutputs,
  streamGenerationProgress,
  STYLE_MAP,
  STYLE_NAMES,
} from '../api'

export const useAppStore = defineStore('app', () => {
  // 状态
  const events = ref([])
  const currentGeneration = ref(null)
  const currentOutput = ref(null)
  const generating = ref(false)
  const progress = ref(0)

  // 计算属性
  const memoryIds = computed(() => events.value.map(e => e.memoryId).filter(Boolean))

  // 方法
  function addEvent(text, memoryId = null) {
    const now = new Date()
    const time = now.toTimeString().slice(0, 5)
    events.value.unshift({
      title: text.length > 15 ? text.slice(0, 15) + '...' : text,
      time,
      memoryId,
      text,
    })
  }

  function removeEvent(index) {
    events.value.splice(index, 1)
  }

  async function saveMemory(text, files) {
    const today = new Date().toISOString().split('T')[0]
    const memory = await createMemory({
      content_text: text || null,
      memory_date: today,
    })

    for (const file of files) {
      await uploadMedia(memory.id, file)
    }

    addEvent(text || '添加了媒体文件', memory.id)
    return memory
  }

  async function generateStory(styleKey) {
    if (memoryIds.value.length === 0) {
      throw new Error('请先添加事件记录')
    }

    const backendStyle = STYLE_MAP[styleKey] || 'watercolor'
    generating.value = true
    progress.value = 0

    try {
      const generation = await createGeneration({
        memory_ids: memoryIds.value,
        type: 'diary',
        style_key: backendStyle,
      })

      return new Promise((resolve, reject) => {
        streamGenerationProgress(generation.id, {
          onProgress: (data) => {
            progress.value = data.progress || 0
          },
          onComplete: async (data) => {
            // Check if it needs confirmation (two-stage workflow)
            if (data.status === 'pending_confirmation') {
              // We need to confirm it to trigger image generation
              try {
                // By default, just use whatever the LLM generated as the final prompt
                const promptToUse = data.user_edited_prompt || data.llm_polished_prompt || 'A beautiful memory'
                const confirmedData = await import('../api').then(m => m.confirmPrompt(data.generation_id, promptToUse))
                
                // Set up a new stream listener for the second stage
                streamGenerationProgress(confirmedData.id, {
                  onProgress: (stage2Data) => {
                    progress.value = 50 + ((stage2Data.progress || 0) / 2) // scale progress for stage 2
                  },
                  onComplete: async (finalData) => {
                    generating.value = false
                    currentGeneration.value = finalData
                    try {
                      const outputs = await getGenerationOutputs(finalData.generation_id)
                      currentOutput.value = outputs[0] || null
                    } catch (e) {
                      console.error('加载输出失败:', e)
                    }
                    events.value = []
                    resolve(finalData)
                  },
                  onError: (error) => {
                    generating.value = false
                    reject(new Error('图片生成失败'))
                  }
                })
              } catch (e) {
                generating.value = false
                reject(new Error('确认生成失败'))
              }
              return
            }

            generating.value = false
            currentGeneration.value = data

            // 加载生成结果
            try {
              const outputs = await getGenerationOutputs(data.generation_id)
              currentOutput.value = outputs[0] || null
            } catch (e) {
              console.error('加载输出失败:', e)
            }

            // 清空事件
            events.value = []
            resolve(data)
          },
          onError: (error) => {
            generating.value = false
            reject(new Error('生成失败'))
          },
        })
      })
    } catch (error) {
      generating.value = false
      throw error
    }
  }

  async function loadDayData(date) {
    const [memoriesResult, generations] = await Promise.all([
      listMemories({ date }),
      listGenerations({ date }),
    ])

    const memories = memoriesResult.memories || []

    // 加载每个记忆的媒体
    const media = []
    for (const mem of memories) {
      try {
        const memMedia = await getMemoryMedia(mem.id)
        media.push(...memMedia)
      } catch (e) {}
    }

    // Load outputs for each generation
    const generationsWithOutputs = await Promise.all((generations || []).map(async gen => {
      try {
        const outputs = await getGenerationOutputs(gen.id);
        return { ...gen, outputs };
      } catch (e) {
        return { ...gen, outputs: [] };
      }
    }));

    return { memories, generations: generationsWithOutputs, media }
  }

  async function loadMonthDates(year, month) {
    const startDate = new Date(year, month, 1)
    const endDate = new Date(year, month + 1, 0)
    
    const startStr = `${startDate.getFullYear()}-${String(startDate.getMonth() + 1).padStart(2, '0')}-01`
    const endStr = `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`

    const generations = await listGenerations({
      start_date: startStr,
      end_date: endStr,
      limit: 100 // Should be enough for a month
    })

    const daysWithData = new Set()
    for (const gen of generations) {
      if (gen.created_at) {
        const d = new Date(gen.created_at)
        daysWithData.add(d.getDate())
      }
    }
    
    return Array.from(daysWithData)
  }

  async function loadGenerationDetails(generation) {
    const [outputs, memories, media] = await Promise.all([
      getGenerationOutputs(generation.id).catch(() => []),
      Promise.all((generation.memory_ids || []).map(id => getMemory(id).catch(() => null))),
      Promise.all((generation.memory_ids || []).map(id => getMemoryMedia(id).catch(() => []))),
    ])

    return {
      generation,
      output: outputs[0] || null,
      memories: memories.filter(Boolean),
      media: media.flat(),
    }
  }

  return {
    events,
    currentGeneration,
    currentOutput,
    generating,
    progress,
    memoryIds,
    addEvent,
    removeEvent,
    saveMemory,
    generateStory,
    loadDayData,
    loadMonthDates,
    loadGenerationDetails,
  }
})
