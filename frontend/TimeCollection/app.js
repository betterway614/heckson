/**
 * YOU TIME Vue3 应用
 */

// ============================================
// Toast 通知组件
// ============================================
const Toast = {
    container: null,

    init() {
        this.container = document.getElementById('toast-container');
    },

    show({ type = 'info', title = '', message = '', duration = 3000 }) {
        if (!this.container) this.init();

        const icons = {
            success: '✓',
            error: '✕',
            warning: '!',
            info: 'i'
        };

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
            ${duration > 0 ? `<div class="toast-progress" style="animation-duration: ${duration}ms"></div>` : ''}
        `;

        this.container.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => {
                toast.classList.add('toast-exit');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    },

    success(message, title = '成功') {
        return this.show({ type: 'success', title, message });
    },

    error(message, title = '错误') {
        return this.show({ type: 'error', title, message, duration: 5000 });
    },

    warning(message, title = '警告') {
        return this.show({ type: 'warning', title, message, duration: 4000 });
    },

    info(message, title = '提示') {
        return this.show({ type: 'info', title, message });
    }
};

const { createApp, ref, computed, reactive, onMounted, watch, nextTick } = Vue;

const app = createApp({
    setup() {
        // ==================== 状态 ====================
        const currentPage = ref('home');
        const generating = ref(false);
        const progress = ref(0);
        const API_BASE_URL = 'http://localhost:8000';

        // 首页状态
        const memoryText = ref('');
        const selectedStyle = ref('default');
        const pendingFiles = ref([]);
        const events = ref([]);

        // 回忆过去弹窗状态
        const showPastModal = ref(false);
        const pastDate = ref('');
        const pastMemoryText = ref('');
        const pastFiles = ref([]);
        const pastEvents = ref([]);

        // 日记页状态
        const currentYear = ref(new Date().getFullYear());
        const currentMonth = ref(new Date().getMonth());
        const selectedDate = ref(null);
        const dayMemories = ref([]);
        const dayGenerations = ref([]);
        const dayMedia = ref([]);
        const currentGeneration = ref(null);
        const currentGenerationOutput = ref(null);

        // 日期选择器状态
        const showDatePicker = ref(false);
        const pickerYear = ref(new Date().getFullYear());
        const pickerMonth = ref(new Date().getMonth());
        const pickerDay = ref(new Date().getDate());

        // 故事详情页状态
        const activeTab = ref('polished');
        const storyContent = ref('');
        const highlightText = ref('润色稿');
        const showOriginal = ref(true);
        const showEditModal = ref(false);
        const editText = ref('');
        const currentMedia = ref([]);
        const currentMemories = ref([]);

        // 故事集状态
        const groupedMemories = ref({});

        // 生成故事集状态
        const selectedGenerations = ref([]);
        const availableGenerations = ref([]);
        const showComicSelect = ref(false);
        const selectedTemplate = ref('record');
        const generatingCollection = ref(false);

        // 视频生成状态
        const showVideoGenModal = ref(false);
        const videoStartDate = ref('');
        const videoEndDate = ref('');
        const videoStyle = ref('cinematic');
        const videoResolution = ref('1280x720');
        const videoStyles = ref({});
        const generatingVideo = ref(false);
        const videoProgress = ref(0);
        const currentVideoGeneration = ref(null);
        const videoScript = ref('');
        const showScriptPreview = ref(false);
        const showVideoPlayer = ref(false);
        const videoUrl = ref('');

        // 预设时间范围
        const presetRanges = [
            { label: '最近7天', days: 7 },
            { label: '最近30天', days: 30 },
            { label: '最近90天', days: 90 }
        ];

        // 分辨率选项
        const resolutionOptions = [
            { value: '1280x720', label: '720p 横屏' },
            { value: '720x1280', label: '720p 竖屏' },
            { value: '1920x1080', label: '1080p 横屏' },
            { value: '1080x1920', label: '1080p 竖屏' }
        ];

        // 全屏预览状态
        const lightbox = reactive({
            show: false,
            items: [],
            index: 0,
            currentItem: null
        });

        // 常量
        const storyTabs = [
            { key: 'original', label: '原文' },
            { key: 'polished', label: '润色稿' },
            { key: 'wechat', label: '朋友圈' },
            { key: 'xiaohongshu', label: '小红书' }
        ];

        const storyTemplates = [
            { key: 'record', icon: '📖', label: '生成记录' },
            { key: 'drama', icon: '🎬', label: '生成爽剧' }
        ];

        // 风格映射
        const STYLE_MAP = {
            'default': 'watercolor',
            'warm': 'watercolor',
            'cool': 'manga_jp',
            'humor': 'cartoon',
            'dramatic': 'comic_shuangwen'
        };

        const STYLE_NAMES = {
            'watercolor': '水彩手绘',
            'manga_jp': '日式漫画',
            'american_retro': '美式复古',
            'cyberpunk': '赛博朋克',
            'picture_book': '绘本风',
            'ink_wash': '水墨风',
            'pixel_art': '像素风',
            'oil_painting': '油画风',
            'line_drawing': '线稿风',
            'cartoon': '卡通风',
            'realistic': '写实风',
            'fantasy': '奇幻风',
            'comic_shuangwen': '高光爽文',
            'comic_zhiyu': '治愈温馨',
            'comic_timeline': '一天记录'
        };

        // ==================== 计算属性 ====================
        const calendarDays = computed(() => {
            const days = [];
            const firstDay = new Date(currentYear.value, currentMonth.value, 1).getDay();
            const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate();
            const today = new Date();

            for (let i = 0; i < firstDay; i++) {
                days.push({ type: 'empty', day: '' });
            }

            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = `${currentYear.value}-${String(currentMonth.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                days.push({
                    type: 'selectable',
                    day,
                    date: dateStr
                });
            }

            return days;
        });

        const yearRange = computed(() => {
            const current = new Date().getFullYear();
            return Array.from({ length: 11 }, (_, i) => current - 5 + i);
        });

        const daysInPickerMonth = computed(() => {
            return new Date(pickerYear.value, pickerMonth.value + 1, 0).getDate();
        });

        // ==================== 方法 ====================

        function getStyleName(key) {
            return STYLE_NAMES[key] || key;
        }

        // 文件上传处理
        function handleFileUpload(e) {
            const files = e.target.files;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const isImage = file.type.startsWith('image/');
                const isVideo = file.type.startsWith('video/');

                if (isImage || isVideo) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        pendingFiles.value.push({
                            file,
                            type: isImage ? 'image' : 'video',
                            preview: event.target.result
                        });
                    };
                    reader.readAsDataURL(file);
                }
            }
            e.target.value = '';
        }

        function removeFile(index) {
            pendingFiles.value.splice(index, 1);
        }

        function handlePastFileUpload(e) {
            const files = e.target.files;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const isImage = file.type.startsWith('image/');
                const isVideo = file.type.startsWith('video/');

                if (isImage || isVideo) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        pastFiles.value.push({
                            file,
                            type: isImage ? 'image' : 'video',
                            preview: event.target.result
                        });
                    };
                    reader.readAsDataURL(file);
                }
            }
            e.target.value = '';
        }

        function removePastFile(index) {
            pastFiles.value.splice(index, 1);
        }

        function addEvent(text, memoryId = null) {
            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
                           now.getMinutes().toString().padStart(2, '0');
            events.value.unshift({
                title: text.length > 15 ? text.substring(0, 15) + '...' : text,
                time: timeStr,
                memoryId,
                text
            });
        }

        function removeEvent(index) {
            events.value.splice(index, 1);
        }

        async function confirmMemory() {
            const text = memoryText.value.trim();
            const validFiles = pendingFiles.value;

            if (text === '' && validFiles.length === 0) {
                Toast.warning('请上传图片或输入回忆内容');
                return;
            }

            try {
                const today = new Date().toISOString().split('T')[0];
                const memory = await createMemory({
                    content_text: text || null,
                    memory_date: today
                });

                for (const fileObj of validFiles) {
                    await uploadMedia(memory.id, fileObj.file);
                }

                addEvent(text || '添加了媒体文件', memory.id);
                memoryText.value = '';
                pendingFiles.value = [];
                Toast.success('回忆已记录！');
            } catch (error) {
                console.error('创建记忆失败:', error);
                Toast.error('保存失败，请重试');
            }
        }

        function startRecording() {
            Toast.info('语音录制功能开发中...');
        }

        async function generateStory() {
            const memoryIds = events.value.map(e => e.memoryId).filter(id => id);
            if (memoryIds.length === 0) {
                Toast.warning('请先添加事件记录');
                return;
            }

            const backendStyle = STYLE_MAP[selectedStyle.value] || 'watercolor';

            try {
                generating.value = true;
                progress.value = 0;

                const generation = await createGeneration({
                    memory_ids: memoryIds,
                    type: 'diary',
                    style_key: backendStyle
                });

                streamGenerationProgress(generation.id, {
                    onProgress: (data) => {
                        progress.value = data.progress || 0;
                    },
                    onComplete: async (data) => {
                        generating.value = false;
                        if (data.status === 'pending_confirmation' || data.status === 'done') {
                            currentGeneration.value = data;
                            await loadGenerationDetails(data);
                            currentPage.value = 'story';
                        }
                    },
                    onError: (error) => {
                        generating.value = false;
                        Toast.error('生成失败，请重试');
                    }
                });

                events.value = [];
                memoryText.value = '';
                pendingFiles.value = [];
            } catch (error) {
                generating.value = false;
                console.error('创建生成任务失败:', error);
                Toast.error('创建失败，请重试');
            }
        }

        async function loadGenerationDetails(generation) {
            try {
                // 加载生成结果
                const outputs = await getGenerationOutputs(generation.id);
                if (outputs.length > 0) {
                    currentGenerationOutput.value = outputs[0];
                }

                // 加载关联的记忆
                if (generation.memory_ids?.length > 0) {
                    const memories = [];
                    const media = [];

                    for (const memId of generation.memory_ids) {
                        try {
                            const mem = await getMemory(memId);
                            memories.push(mem);
                            const memMedia = await getMemoryMedia(memId);
                            media.push(...memMedia);
                        } catch (e) {
                            console.error('加载记忆详情失败:', e);
                        }
                    }

                    currentMemories.value = memories;
                    currentMedia.value = media;
                }

                // 设置初始内容
                if (generation.vlm_raw_metadata) {
                    const diary = typeof generation.vlm_raw_metadata === 'string'
                        ? generation.vlm_raw_metadata
                        : generation.vlm_raw_metadata.diary || JSON.stringify(generation.vlm_raw_metadata);
                    storyContent.value = `<p>${diary}</p>`;
                    editText.value = diary;
                }

                highlightText.value = '润色稿';
                activeTab.value = 'polished';
            } catch (error) {
                console.error('加载详情失败:', error);
            }
        }

        async function switchTab(tabKey) {
            activeTab.value = tabKey;

            if (tabKey === 'original') {
                if (currentGeneration.value?.vlm_raw_metadata) {
                    const diary = typeof currentGeneration.value.vlm_raw_metadata === 'string'
                        ? currentGeneration.value.vlm_raw_metadata
                        : currentGeneration.value.vlm_raw_metadata.diary || JSON.stringify(currentGeneration.value.vlm_raw_metadata);
                    storyContent.value = `<p>${diary}</p>`;
                }
                highlightText.value = '原文';
                return;
            }

            const POLISH_STYLE_MAP = {
                'polished': 'polished',
                'wechat': 'moments',
                'xiaohongshu': 'xiaohongshu'
            };

            const polishStyle = POLISH_STYLE_MAP[tabKey];
            if (!polishStyle || !currentGeneration.value) return;

            try {
                storyContent.value = '<p>AI润色中...</p>';
                const originalText = currentGeneration.value.vlm_raw_metadata?.diary ||
                                    (typeof currentGeneration.value.vlm_raw_metadata === 'string' ? currentGeneration.value.vlm_raw_metadata : '');

                const result = await polishDiary(currentGeneration.value.id, {
                    diary_text: originalText,
                    style_key: polishStyle
                });

                storyContent.value = `<p>${result.polished_text}</p>`;
                editText.value = result.polished_text;
                highlightText.value = tabKey === 'wechat' ? '朋友圈分享' : tabKey === 'xiaohongshu' ? '小红书风格' : '润色稿';
            } catch (error) {
                console.error('润色失败:', error);
                storyContent.value = '<p>润色失败，请重试</p>';
            }
        }

        function openEditModal() {
            editText.value = storyContent.value.replace(/<[^>]+>/g, '');
            showEditModal.value = true;
        }

        async function saveEdit() {
            if (currentGeneration.value) {
                try {
                    await updatePrompt(currentGeneration.value.id, {
                        user_edited_prompt: editText.value
                    });
                } catch (error) {
                    console.error('保存编辑失败:', error);
                }
            }
            storyContent.value = '<p>' + editText.value.replace(/\n/g, '</p><p>') + '</p>';
            showEditModal.value = false;
        }

        function prevMonth() {
            if (currentMonth.value === 0) {
                currentMonth.value = 11;
                currentYear.value--;
            } else {
                currentMonth.value--;
            }
        }

        function nextMonth() {
            if (currentMonth.value === 11) {
                currentMonth.value = 0;
                currentYear.value++;
            } else {
                currentMonth.value++;
            }
        }

        async function selectDate(day) {
            if (day.type !== 'selectable') return;
            selectedDate.value = day.date;

            try {
                const memoriesResult = await listMemories({ date: day.date });
                dayMemories.value = memoriesResult.memories || [];

                // 加载每个记忆的媒体
                const allMedia = [];
                for (const mem of dayMemories.value) {
                    try {
                        const media = await getMemoryMedia(mem.id);
                        allMedia.push(...media);
                    } catch (e) {}
                }
                dayMedia.value = allMedia;

                const generations = await listGenerations({ date: day.date });
                dayGenerations.value = generations || [];

                if (generations.length > 0) {
                    currentGeneration.value = generations[0];
                    const outputs = await getGenerationOutputs(generations[0].id);
                    currentGenerationOutput.value = outputs[0] || null;
                } else {
                    currentGeneration.value = null;
                    currentGenerationOutput.value = null;
                }
            } catch (error) {
                console.error('查询记忆失败:', error);
            }
        }

        function confirmDatePicker() {
            currentYear.value = pickerYear.value;
            currentMonth.value = pickerMonth.value;
            showDatePicker.value = false;
            const dateStr = `${pickerYear.value}-${String(pickerMonth.value + 1).padStart(2, '0')}-${String(pickerDay.value).padStart(2, '0')}`;
            selectDate({ type: 'selectable', date: dateStr });
        }

        async function viewGeneration(gen) {
            currentGeneration.value = gen;
            await loadGenerationDetails(gen);
            currentPage.value = 'story';
        }

        function formatTime(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.getHours().toString().padStart(2, '0') + ':' + date.getMinutes().toString().padStart(2, '0');
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
        }

        function formatGroupDate(dateStr) {
            if (!dateStr) return '';
            const parts = dateStr.split('-');
            return `${parseInt(parts[1])}月${parseInt(parts[2])}日`;
        }

        async function switchToDiary() {
            currentPage.value = 'diary';
            const today = new Date();
            currentYear.value = today.getFullYear();
            currentMonth.value = today.getMonth();
            const todayStr = today.toISOString().split('T')[0];
            await selectDate({ type: 'selectable', date: todayStr });
        }

        async function switchToStories() {
            currentPage.value = 'stories';
            await loadStoriesList();
        }

        async function loadStoriesList() {
            try {
                const endDate = new Date().toISOString().split('T')[0];
                const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
                const result = await listMemories({ start_date: startDate, end_date: endDate, limit: 100 });

                // 按日期分组并加载媒体
                const grouped = {};
                for (const memory of result.memories || []) {
                    const date = memory.memory_date;
                    if (!grouped[date]) grouped[date] = [];
                    try {
                        const media = await getMemoryMedia(memory.id);
                        memory.media = media;
                    } catch (e) {
                        memory.media = [];
                    }
                    grouped[date].push(memory);
                }
                groupedMemories.value = grouped;
            } catch (error) {
                console.error('加载故事集失败:', error);
            }
        }

        function viewStoryGroup(date) {
            const parts = date.split('-');
            currentYear.value = parseInt(parts[0]);
            currentMonth.value = parseInt(parts[1]) - 1;
            selectDate({ type: 'selectable', date });
            currentPage.value = 'diary';
        }

        // 全屏预览
        function openLightbox(index) {
            lightbox.items = dayMedia.value.map(m => ({
                type: 'image',
                src: API_BASE_URL + '/uploads/' + m.file_path
            }));
            lightbox.index = index;
            lightbox.currentItem = lightbox.items[index];
            lightbox.show = true;
        }

        function openLightboxMedia(index) {
            lightbox.items = currentMedia.value.map(m => ({
                type: 'image',
                src: API_BASE_URL + '/uploads/' + m.file_path
            }));
            lightbox.index = index;
            lightbox.currentItem = lightbox.items[index];
            lightbox.show = true;
        }

        function closeLightbox() {
            lightbox.show = false;
        }

        function prevLightbox() {
            if (lightbox.index > 0) {
                lightbox.index--;
                lightbox.currentItem = lightbox.items[lightbox.index];
            }
        }

        function nextLightbox() {
            if (lightbox.index < lightbox.items.length - 1) {
                lightbox.index++;
                lightbox.currentItem = lightbox.items[lightbox.index];
            }
        }

        // 回忆过去
        function addPastEvent(text) {
            pastEvents.value.push({ title: text.length > 15 ? text.substring(0, 15) + '...' : text, text });
        }

        function removePastEvent(index) {
            pastEvents.value.splice(index, 1);
        }

        function confirmPastMemory() {
            const text = pastMemoryText.value.trim();
            if (text === '' && pastFiles.value.length === 0) {
                Toast.warning('请上传图片或输入回忆内容');
                return;
            }
            addPastEvent(text || '添加了媒体文件');
            pastMemoryText.value = '';
            pastFiles.value = [];
            Toast.success('回忆已记录！');
        }

        async function savePastMemory() {
            if (!pastDate.value) {
                Toast.warning('请选择日期');
                return;
            }
            if (pastFiles.value.length === 0 && pastEvents.value.length === 0) {
                Toast.warning('请上传图片或输入故事回忆');
                return;
            }

            try {
                const memory = await createMemory({
                    content_text: pastEvents.value.map(e => e.text).join('\n') || null,
                    memory_date: pastDate.value
                });

                for (const fileObj of pastFiles.value) {
                    await uploadMedia(memory.id, fileObj.file);
                }

                events.value.unshift({
                    title: pastEvents.value[0]?.title || '过去的回忆',
                    time: formatGroupDate(pastDate.value),
                    memoryId: memory.id
                });

                showPastModal.value = false;
                pastDate.value = '';
                pastMemoryText.value = '';
                pastFiles.value = [];
                pastEvents.value = [];
                Toast.success('过去回忆已保存！');
            } catch (error) {
                console.error('保存失败:', error);
                Toast.error('保存失败，请重试');
            }
        }

        // 生成故事集
        const isGenerationSelected = (id) => selectedGenerations.value.some(g => g.id === id);

        function toggleGenerationSelection(id) {
            const index = selectedGenerations.value.findIndex(g => g.id === id);
            if (index >= 0) {
                selectedGenerations.value.splice(index, 1);
            } else {
                const gen = availableGenerations.value.find(g => g.id === id);
                if (gen) selectedGenerations.value.push(gen);
            }
        }

        function removeSelectedGeneration(id) {
            const index = selectedGenerations.value.findIndex(g => g.id === id);
            if (index >= 0) selectedGenerations.value.splice(index, 1);
        }

        function confirmComicSelection() {
            showComicSelect.value = false;
        }

        async function generateStoryCollection() {
            if (selectedGenerations.value.length === 0) {
                Toast.warning('请先选择漫画');
                return;
            }
            Toast.info('故事集生成功能开发中...');
        }

        // ==================== 视频生成相关 ====================

        // 选择预设时间范围
        function selectPresetRange(days) {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - days);

            videoStartDate.value = start.toISOString().split('T')[0];
            videoEndDate.value = end.toISOString().split('T')[0];
        }

        // 加载视频风格
        async function loadVideoStyles() {
            try {
                videoStyles.value = await listVideoStyles();
            } catch (error) {
                console.error('加载视频风格失败:', error);
            }
        }

        // 生成视频
        async function generateVideo() {
            if (!videoStartDate.value || !videoEndDate.value) {
                alert('请选择时间范围');
                return;
            }

            try {
                generatingVideo.value = true;
                videoProgress.value = 0;

                // 1. 创建视频生成任务
                const generation = await createVideoGeneration({
                    start_date: videoStartDate.value,
                    end_date: videoEndDate.value,
                    style: videoStyle.value,
                    resolution: videoResolution.value
                });

                currentVideoGeneration.value = generation;

                // 2. 监听进度
                streamGenerationProgress(generation.id, {
                    onProgress: (data) => {
                        videoProgress.value = data.progress || 0;
                    },
                    onComplete: (data) => {
                        generatingVideo.value = false;

                        if (data.status === 'pending_confirmation') {
                            // 脚本生成完成，显示脚本预览
                            videoScript.value = data.video_script || '';
                            showVideoGenModal.value = false;
                            showScriptPreview.value = true;
                        } else if (data.status === 'done') {
                            // 视频生成完成，显示视频播放器
                            videoUrl.value = data.video_url;
                            showScriptPreview.value = false;
                            showVideoPlayer.value = true;
                        }
                    },
                    onError: (error) => {
                        generatingVideo.value = false;
                        console.error('视频生成失败:', error);
                        alert('视频生成失败，请重试');
                    }
                });

            } catch (error) {
                generatingVideo.value = false;
                console.error('创建视频生成任务失败:', error);
                alert('创建失败，请重试');
            }
        }

        // 确认脚本，生成视频
        async function confirmScript() {
            if (!currentVideoGeneration.value) return;

            try {
                generatingVideo.value = true;
                videoProgress.value = 0;

                // 更新脚本（如果用户编辑了）
                await updateVideoScript(currentVideoGeneration.value.id, videoScript.value);

                // 确认生成视频
                await confirmVideoGeneration(currentVideoGeneration.value.id);

                // 监听进度
                streamGenerationProgress(currentVideoGeneration.value.id, {
                    onProgress: (data) => {
                        videoProgress.value = data.progress || 0;
                    },
                    onComplete: (data) => {
                        generatingVideo.value = false;

                        if (data.status === 'done') {
                            videoUrl.value = data.video_url;
                            showScriptPreview.value = false;
                            showVideoPlayer.value = true;
                        }
                    },
                    onError: (error) => {
                        generatingVideo.value = false;
                        console.error('视频生成失败:', error);
                        alert('视频生成失败，请重试');
                    }
                });

            } catch (error) {
                generatingVideo.value = false;
                console.error('确认脚本失败:', error);
                alert('确认失败，请重试');
            }
        }

        watch(showComicSelect, async (val) => {
            if (val) {
                try {
                    const result = await listGenerations({ limit: 50 });
                    availableGenerations.value = result || [];
                } catch (error) {
                    console.error('加载生成记录失败:', error);
                }
            }
        });

        onMounted(() => {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            pastDate.value = yesterday.toISOString().split('T')[0];
            loadVideoStyles();
        });

        return {
            currentPage, generating, progress, API_BASE_URL,
            memoryText, selectedStyle, pendingFiles, events,
            showPastModal, pastDate, pastMemoryText, pastFiles, pastEvents,
            currentYear, currentMonth, selectedDate, dayMemories, dayGenerations, dayMedia,
            currentGeneration, currentGenerationOutput,
            showDatePicker, pickerYear, pickerMonth, pickerDay,
            activeTab, storyContent, highlightText, showOriginal, showEditModal, editText,
            currentMedia, currentMemories,
            groupedMemories, selectedGenerations, availableGenerations, showComicSelect,
            selectedTemplate, generatingCollection, lightbox,
            storyTabs, storyTemplates, STYLE_MAP,
            calendarDays, yearRange, daysInPickerMonth,
            getStyleName, handleFileUpload, removeFile, handlePastFileUpload, removePastFile,
            addEvent, removeEvent, confirmMemory, startRecording, generateStory,
            switchTab, openEditModal, saveEdit,
            prevMonth, nextMonth, selectDate, confirmDatePicker,
            viewGeneration, formatTime, formatDate, formatGroupDate,
            switchToDiary, switchToStories, viewStoryGroup,
            openLightbox, openLightboxMedia, closeLightbox, prevLightbox, nextLightbox,
            addPastEvent, removePastEvent, confirmPastMemory, savePastMemory,
            isGenerationSelected, toggleGenerationSelection, removeSelectedGeneration,
            confirmComicSelection, generateStoryCollection,
            showVideoGenModal, videoStartDate, videoEndDate, videoStyle, videoResolution,
            videoStyles, generatingVideo, videoProgress, currentVideoGeneration,
            videoScript, showScriptPreview, showVideoPlayer, videoUrl,
            presetRanges, resolutionOptions,
            selectPresetRange, generateVideo, confirmScript
        };
    }
});

app.mount('#app');
