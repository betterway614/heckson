// 页面切换函数
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
    document.getElementById('nav-' + pageId.replace('-page', '')).classList.add('active');
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 底部导航点击事件
    document.getElementById('nav-home').addEventListener('click', function() {
        showPage('home-page');
    });

    document.getElementById('nav-diary').addEventListener('click', function() {
        showPage('diary-page');
    });

    document.getElementById('nav-stories').addEventListener('click', function() {
        showPage('stories-page');
    });

    // 图片上传处理
    document.getElementById('image-upload').addEventListener('change', function(e) {
        const files = e.target.files;
        const previewContainer = document.getElementById('upload-preview');
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const previewItem = document.createElement('div');
                    previewItem.className = 'upload-preview-item';
                    previewItem.innerHTML = `
                        <img src="${event.target.result}" alt="上传图片">
                        <span class="remove-upload">×</span>
                    `;
                    previewContainer.appendChild(previewItem);
                    
                    // 添加删除事件
                    previewItem.querySelector('.remove-upload').addEventListener('click', function() {
                        previewItem.remove();
                        updatePhotoCount();
                    });
                    
                    updatePhotoCount();
                };
                reader.readAsDataURL(file);
            }
        }
        
        // 清空input以便重新选择
        this.value = '';
    });

    // 更新照片数量
    function updatePhotoCount() {
        const count = document.querySelectorAll('.upload-preview-item').length;
        document.getElementById('photo-count').textContent = `照片 ${count}`;
    }

    // 回忆文字输入字数统计
    document.getElementById('memories-textarea').addEventListener('input', function() {
        const count = this.value.length;
        document.querySelector('.char-count').textContent = `${count}/500`;
        
        if (count > 500) {
            this.value = this.value.substring(0, 500);
            document.querySelector('.char-count').textContent = '500/500';
        }
    });

    // 确认回忆按钮 - 添加事件记录
    document.getElementById('confirm-memories-btn').addEventListener('click', function() {
        const text = document.getElementById('memories-textarea').value.trim();
        const hasImages = document.querySelectorAll('#upload-preview .upload-preview-item').length > 0;
        
        if (text === '' && !hasImages) {
            alert('请上传图片或输入回忆内容');
            return;
        }
        
        // 如果没有文字但有图片，使用默认标题
        const eventText = text || '添加了一张照片';
        
        // 创建事件记录
        addEvent(eventText);
        
        // 清空输入框
        document.getElementById('memories-textarea').value = '';
        document.querySelector('.char-count').textContent = '0/500';
        
        // 清空图片预览
        const previewContainer = document.getElementById('upload-preview');
        previewContainer.innerHTML = '';
        updatePhotoCount();
        
        alert('回忆已记录！');
    });

    // 添加事件记录函数
    function addEvent(text) {
        const eventsList = document.getElementById('events-list');
        const eventsCount = document.getElementById('events-count');
        
        // 生成标题（取前15个字）
        const title = text.length > 15 ? text.substring(0, 15) + '...' : text;
        
        // 获取当前时间
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        
        // 创建事件项
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.innerHTML = `
            <div class="event-icon">
                <i class="fas fa-star"></i>
            </div>
            <div class="event-content">
                <span class="event-title">${title}</span>
                <span class="event-time">${timeStr}</span>
            </div>
            <div class="remove-event">
                <button class="remove-event-btn">×</button>
            </div>
        `;
        
        // 添加到列表开头
        eventsList.insertBefore(eventItem, eventsList.firstChild);
        
        // 更新计数
        const count = eventsList.querySelectorAll('.event-item').length;
        eventsCount.textContent = count;
        
        // 添加删除事件
        eventItem.querySelector('.remove-event-btn').addEventListener('click', function() {
            eventItem.remove();
            const newCount = eventsList.querySelectorAll('.event-item').length;
            eventsCount.textContent = newCount;
        });
    }

    // 回忆过去按钮 - 打开弹窗
    document.getElementById('past-card').addEventListener('click', function() {
        document.getElementById('past-modal').classList.remove('hidden');
        // 设置默认日期为昨天
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const dateStr = yesterday.toISOString().split('T')[0];
        document.getElementById('past-date-input').value = dateStr;
    });

    // 关闭弹窗
    document.getElementById('close-past-modal').addEventListener('click', function() {
        document.getElementById('past-modal').classList.add('hidden');
        clearPastModal();
    });

    // 点击弹窗外部关闭
    document.getElementById('past-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.add('hidden');
            clearPastModal();
        }
    });

    // 过去图片上传处理
    document.getElementById('past-image-upload').addEventListener('change', function(e) {
        const files = e.target.files;
        const previewContainer = document.getElementById('past-upload-preview');
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const previewItem = document.createElement('div');
                    previewItem.className = 'upload-preview-item';
                    previewItem.innerHTML = `
                        <img src="${event.target.result}" alt="上传图片">
                        <span class="remove-upload">×</span>
                    `;
                    previewContainer.appendChild(previewItem);
                    
                    previewItem.querySelector('.remove-upload').addEventListener('click', function() {
                        previewItem.remove();
                        updatePastPhotoCount();
                    });
                    
                    updatePastPhotoCount();
                };
                reader.readAsDataURL(file);
            }
        }
        this.value = '';
    });

    // 更新过去照片数量
    function updatePastPhotoCount() {
        const count = document.querySelectorAll('#past-upload-preview .upload-preview-item').length;
        document.getElementById('past-photo-count').textContent = `照片 ${count}`;
    }

    // 过去回忆按钮点击
    document.getElementById('past-memories-btn').addEventListener('click', function() {
        document.getElementById('past-memories-textarea').focus();
    });

    // 过去回忆文字输入字数统计
    document.getElementById('past-memories-textarea').addEventListener('input', function() {
        const count = this.value.length;
        document.querySelector('.past-char-count').textContent = `${count}/500`;
    });

    // 过去确认记录按钮 - 添加到弹窗内的事件列表
    document.getElementById('past-confirm-memories-btn').addEventListener('click', function() {
        const text = document.getElementById('past-memories-textarea').value.trim();
        const hasImages = document.querySelectorAll('#past-upload-preview .upload-preview-item').length > 0;
        
        if (text === '' && !hasImages) {
            alert('请上传图片或输入回忆内容');
            return;
        }
        
        // 如果没有文字但有图片，使用默认标题
        let title = text || '添加了一张照片';
        if (title.length > 15) {
            title = title.substring(0, 15) + '...';
        }
        
        // 添加到弹窗内的事件列表
        const pastEventsList = document.getElementById('past-events-list');
        const pastEventsCount = document.getElementById('past-events-count');
        
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.innerHTML = `
            <div class="event-icon">
                <i class="fas fa-star"></i>
            </div>
            <div class="event-content">
                <span class="event-title">${title}</span>
                <span class="event-time">刚刚</span>
            </div>
            <div class="remove-event">
                <button class="remove-event-btn">×</button>
            </div>
        `;
        
        pastEventsList.insertBefore(eventItem, pastEventsList.firstChild);
        
        const count = pastEventsList.querySelectorAll('.event-item').length;
        pastEventsCount.textContent = count;
        
        eventItem.querySelector('.remove-event-btn').addEventListener('click', function() {
            eventItem.remove();
            const newCount = pastEventsList.querySelectorAll('.event-item').length;
            pastEventsCount.textContent = newCount;
        });
        
        // 清空输入框
        document.getElementById('past-memories-textarea').value = '';
        document.querySelector('.past-char-count').textContent = '0/500';
        
        alert('回忆已记录！');
    });

    // 保存过去回忆
    document.getElementById('past-save-btn').addEventListener('click', function() {
        const date = document.getElementById('past-date-input').value;
        
        if (!date) {
            alert('请选择日期');
            return;
        }
        
        const hasImages = document.querySelectorAll('#past-upload-preview .upload-preview-item').length > 0;
        const hasMemories = document.querySelectorAll('#past-events-list .event-item').length > 0;
        
        if (!hasImages && !hasMemories) {
            alert('请上传图片或输入故事回忆');
            return;
        }
        
        // 格式化日期
        const dateObj = new Date(date);
        const dateStr = (dateObj.getMonth() + 1) + '月' + dateObj.getDate() + '日';
        
        // 获取第一条事件记录作为标题
        const firstEvent = document.querySelector('#past-events-list .event-item .event-title');
        let title = firstEvent ? firstEvent.textContent : '过去的回忆';
        if (title.length > 15) {
            title = title.substring(0, 15) + '...';
        }
        
        // 添加到主页的事件列表
        const eventsList = document.getElementById('events-list');
        const eventsCount = document.getElementById('events-count');
        
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.innerHTML = `
            <div class="event-icon" style="background: linear-gradient(135deg, #6B8E23, #9ACD32);">
                <i class="fas fa-history"></i>
            </div>
            <div class="event-content">
                <span class="event-title">${title}</span>
                <span class="event-time">${dateStr}</span>
            </div>
            <div class="remove-event">
                <button class="remove-event-btn">×</button>
            </div>
        `;
        
        eventsList.insertBefore(eventItem, eventsList.firstChild);
        
        const count = eventsList.querySelectorAll('.event-item').length;
        eventsCount.textContent = count;
        
        eventItem.querySelector('.remove-event-btn').addEventListener('click', function() {
            eventItem.remove();
            const newCount = eventsList.querySelectorAll('.event-item').length;
            eventsCount.textContent = newCount;
        });
        
        // 关闭弹窗并清空
        document.getElementById('past-modal').classList.add('hidden');
        clearPastModal();
        alert('过去回忆已保存！');
    });

    // 清空过去回忆弹窗
    function clearPastModal() {
        document.getElementById('past-date-input').value = '';
        document.getElementById('past-memories-textarea').value = '';
        document.querySelector('.past-char-count').textContent = '0/500';
        document.getElementById('past-upload-preview').innerHTML = '';
        document.getElementById('past-photo-count').textContent = '照片 0';
        document.getElementById('past-events-list').innerHTML = '';
        document.getElementById('past-events-count').textContent = '0';
    }

    // 关闭图片预览
    document.getElementById('close-preview').addEventListener('click', function() {
        document.getElementById('image-preview').classList.add('hidden');
    });

    // 日记列表点击事件
    document.querySelectorAll('.comic-item').forEach(item => {
        item.addEventListener('click', function() {
            showPage('story-page');
        });
    });

    // 完成今天的故事按钮 - 跳转到故事详情页
    document.getElementById('comic-btn').addEventListener('click', function() {
        const hasEvents = document.querySelectorAll('#events-list .event-item').length > 0;
        
        if (!hasEvents) {
            alert('请先添加事件记录');
            return;
        }
        
        alert('AI正在生成你的故事漫画...');
        
        // 清空记录
        document.getElementById('events-list').innerHTML = '';
        document.getElementById('events-count').textContent = '0';
        document.getElementById('upload-preview').innerHTML = '';
        document.getElementById('memories-textarea').value = '';
        document.querySelector('.char-count').textContent = '0/500';
        updatePhotoCount();
        
        setTimeout(() => {
            showPage('story-page');
        }, 1500);
    });

    // 年月日选择弹窗
    const datePickerModal = document.getElementById('date-picker-modal');
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const daySelect = document.getElementById('day-select');
    
    // 初始化年月日选择器
    function initDatePicker() {
        const today = new Date();
        const currentYear = today.getFullYear();
        
        // 年份选择器 (前后5年)
        for (let year = currentYear - 5; year <= currentYear + 5; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            if (year === currentYear) option.selected = true;
            yearSelect.appendChild(option);
        }
        
        // 月份选择器
        for (let month = 1; month <= 12; month++) {
            const option = document.createElement('option');
            option.value = month - 1;
            option.textContent = month;
            if (month - 1 === today.getMonth()) option.selected = true;
            monthSelect.appendChild(option);
        }
        
        // 更新日期选择器
        updateDaySelect(currentYear, today.getMonth(), today.getDate());
    }
    
    // 更新日期选择器
    function updateDaySelect(year, month, selectedDay) {
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        daySelect.innerHTML = '';
        
        for (let day = 1; day <= daysInMonth; day++) {
            const option = document.createElement('option');
            option.value = day;
            option.textContent = day;
            if (day === selectedDay) option.selected = true;
            daySelect.appendChild(option);
        }
    }
    
    // 监听年月变化
    yearSelect.addEventListener('change', function() {
        updateDaySelect(parseInt(yearSelect.value), parseInt(monthSelect.value), parseInt(daySelect.value));
    });
    
    monthSelect.addEventListener('change', function() {
        updateDaySelect(parseInt(yearSelect.value), parseInt(monthSelect.value), parseInt(daySelect.value));
    });
    
    // 点击日历标题打开弹窗
    document.getElementById('calendar-title').addEventListener('click', function() {
        const currentYear = parseInt(yearSelect.value);
        const currentMonth = parseInt(monthSelect.value);
        const currentDay = parseInt(daySelect.value);
        
        yearSelect.value = currentYear;
        monthSelect.value = currentMonth;
        updateDaySelect(currentYear, currentMonth, currentDay);
        
        datePickerModal.classList.remove('hidden');
    });
    
    // 关闭弹窗
    document.getElementById('close-date-picker').addEventListener('click', function() {
        datePickerModal.classList.add('hidden');
    });
    
    document.getElementById('date-cancel-btn').addEventListener('click', function() {
        datePickerModal.classList.add('hidden');
    });
    
    // 点击弹窗外部关闭
    datePickerModal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.add('hidden');
        }
    });
    
    // 确认选择
    document.getElementById('date-confirm-btn').addEventListener('click', function() {
        const year = parseInt(yearSelect.value);
        const month = parseInt(monthSelect.value);
        const day = parseInt(daySelect.value);
        
        currentCalendarDate = new Date(year, month, day);
        generateCalendar(year, month);
        
        // 选中新日期
        const targetCell = document.querySelector(`.calendar-cell.selectable[data-date="${day}"]`);
        if (targetCell) {
            document.querySelectorAll('.calendar-cell.active').forEach(c => c.classList.remove('active'));
            targetCell.classList.add('active');
            updateComicByDate(day);
        }
        
        datePickerModal.classList.add('hidden');
    });
    
    // 初始化日期选择器
    initDatePicker();

    // 日历当前月份
    let currentCalendarDate = new Date();
    
    // 生成日历网格
    function generateCalendar(year, month) {
        const calendarGrid = document.getElementById('calendar-grid');
        const calendarTitle = document.querySelector('.calendar-title');
        
        calendarTitle.textContent = year + '年' + (month + 1) + '月';
        
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const today = new Date();
        
        let html = '';
        
        // 空单元格
        for (let i = 0; i < firstDay; i++) {
            html += '<div class="calendar-cell empty"></div>';
        }
        
        // 日期单元格
        for (let day = 1; day <= daysInMonth; day++) {
            const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
            html += `<div class="calendar-cell selectable${isToday ? ' today' : ''}" data-date="${day}">${day}</div>`;
        }
        
        calendarGrid.innerHTML = html;
        
        // 重新绑定日期点击事件
        document.querySelectorAll('.calendar-cell.selectable').forEach(function(cell) {
            cell.addEventListener('click', function() {
                document.querySelectorAll('.calendar-cell.active').forEach(function(c) {
                    c.classList.remove('active');
                });
                this.classList.add('active');
                
                const date = this.dataset.date;
                updateComicByDate(date);
            });
        });
    }
    
    // 初始化日历
    generateCalendar(currentCalendarDate.getFullYear(), currentCalendarDate.getMonth());
    
    // 月份切换
    document.getElementById('calendar-prev').addEventListener('click', function() {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
        generateCalendar(currentCalendarDate.getFullYear(), currentCalendarDate.getMonth());
    });
    
    document.getElementById('calendar-next').addEventListener('click', function() {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
        generateCalendar(currentCalendarDate.getFullYear(), currentCalendarDate.getMonth());
    });

    // 日历日期选择
    document.querySelectorAll('.calendar-cell.selectable').forEach(function(cell) {
        cell.addEventListener('click', function() {
            // 移除其他日期的active状态
            document.querySelectorAll('.calendar-cell.active').forEach(function(c) {
                c.classList.remove('active');
            });
            // 添加当前日期的active状态
            this.classList.add('active');
            
            // 更新漫画和故事脉络（模拟数据）
            const date = this.dataset.date;
            updateComicByDate(date);
        });
    });

    // 根据日期更新漫画
    function updateComicByDate(date) {
        const comicImage = document.getElementById('comic-image');
        const comicTitle = document.getElementById('comic-title');
        const timelineList = document.getElementById('timeline-list');
        
        // 模拟不同日期的漫画数据
        const comicData = {
            '16': {
                title: '晴日的沉默与自省',
                image: 'https://neeko-copilot.bytedance.net/api/text2image?prompt=art%20exhibition%20gallery%20with%20framed%20artworks&image_size=landscape_16_9',
                timeline: [
                    { time: '早晨', content: '睡到自然醒，洗漱、吃饭、收拾屋子' },
                    { time: '上午', content: '享受平静的时光，与日常做一个无声的交易' },
                    { time: '午后', content: '出门散步，听了一场关于技术与依赖的谈话' },
                    { time: '傍晚', content: '回到家，躺着看剧，任意包裹自己' }
                ]
            },
            '15': {
                title: '风很轻的一天',
                image: 'https://neeko-copilot.bytedance.net/api/text2image?prompt=desk%20with%20infinity%20symbol%20sculpture%20and%20pen&image_size=landscape_16_9',
                timeline: [
                    { time: '早晨', content: '早起跑步，感受微风拂面' },
                    { time: '上午', content: '在咖啡馆工作，完成了重要的项目' },
                    { time: '午后', content: '和朋友聚会，聊了很多有趣的话题' },
                    { time: '傍晚', content: '独自看日落，思考人生' }
                ]
            },
            '14': {
                title: '雨天的沉思',
                image: 'https://neeko-copilot.bytedance.net/api/text2image?prompt=rainy%20day%20window%20view%20with%20books%20and%20tea&image_size=landscape_16_9',
                timeline: [
                    { time: '早晨', content: '被雨声唤醒，心情格外宁静' },
                    { time: '上午', content: '阅读一本期待已久的书' },
                    { time: '午后', content: '写日记，记录最近的思考' },
                    { time: '傍晚', content: '煮了一杯热茶，听着雨声入眠' }
                ]
            }
        };
        
        const data = comicData[date] || comicData['16'];
        comicImage.src = data.image;
        comicTitle.textContent = data.title;
        
        // 更新故事脉络
        let timelineHTML = '';
        data.timeline.forEach(function(item) {
            timelineHTML += `
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <h4>${item.time}</h4>
                        <p>${item.content}</p>
                    </div>
                </div>
            `;
        });
        timelineList.innerHTML = timelineHTML;
    }

    document.getElementById('back-from-story').addEventListener('click', function() {
        showPage('home-page');
    });

    // 添加故事集按钮 - 跳转到生成页面
    document.getElementById('add-story-btn').addEventListener('click', function() {
        showPage('generate-story-page');
    });

    // 从生成故事集页面返回
    document.getElementById('back-from-generate').addEventListener('click', function() {
        showPage('stories-page');
    });

    // 删除已选择的漫画
    document.getElementById('generate-selected-list').addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.remove-selected');
        if (removeBtn) {
            const selectedItem = removeBtn.closest('.selected-item');
            selectedItem.remove();
        }
    });

    // 点击+号打开选择漫画弹窗
    document.getElementById('add-comic-btn').addEventListener('click', function() {
        document.getElementById('comic-select-modal').classList.remove('hidden');
        // 默认选中今天
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('comic-date-input').value = today;
        // 重置选中状态
        document.querySelectorAll('.comic-select-item').forEach(item => {
            item.classList.remove('selected');
        });
    });

    // 关闭选择漫画弹窗
    document.getElementById('close-comic-select').addEventListener('click', function() {
        document.getElementById('comic-select-modal').classList.add('hidden');
    });

    // 点击弹窗外部关闭
    document.getElementById('comic-select-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.add('hidden');
        }
    });

    // 选择漫画项目
    document.getElementById('comic-select-list').addEventListener('click', function(e) {
        const item = e.target.closest('.comic-select-item');
        if (item) {
            item.classList.toggle('selected');
        }
    });

    // 确认选择漫画
    document.getElementById('confirm-select-btn').addEventListener('click', function() {
        const selectedItems = document.querySelectorAll('.comic-select-item.selected');
        const selectedList = document.getElementById('generate-selected-list');
        const addBtn = document.getElementById('add-comic-btn');
        
        selectedItems.forEach(item => {
            const id = item.dataset.id;
            const imgSrc = item.querySelector('img').src;
            const title = item.querySelector('h4').textContent;
            
            // 检查是否已存在
            const existingIds = Array.from(document.querySelectorAll('#generate-selected-list .selected-item[data-id]'))
                .map(el => el.dataset.id);
            
            if (!existingIds.includes(id)) {
                const newItem = document.createElement('div');
                newItem.className = 'selected-item';
                newItem.dataset.id = id;
                newItem.innerHTML = `
                    <img src="${imgSrc}" alt="${title}">
                    <span class="remove-selected">×</span>
                `;
                selectedList.insertBefore(newItem, addBtn);
            }
        });
        
        document.getElementById('comic-select-modal').classList.add('hidden');
    });

    // 模板选择
    document.getElementById('template-list').addEventListener('click', function(e) {
        const templateItem = e.target.closest('.template-item');
        if (templateItem) {
            document.querySelectorAll('#template-list .template-item').forEach(item => {
                item.classList.remove('active');
            });
            templateItem.classList.add('active');
        }
    });

    // 编辑按钮
    document.getElementById('edit-btn').addEventListener('click', function() {
        document.getElementById('edit-modal').classList.remove('hidden');
    });

    // 原事件展开/收起
    document.getElementById('toggle-original-btn').addEventListener('click', function() {
        const content = document.getElementById('original-event-content');
        const btn = document.getElementById('toggle-original-btn');
        
        content.classList.toggle('hidden');
        btn.classList.toggle('collapsed');
    });

    // 关闭编辑弹窗
    document.getElementById('close-edit-modal').addEventListener('click', function() {
        document.getElementById('edit-modal').classList.add('hidden');
    });

    // 保存编辑
    document.querySelector('.modal-save').addEventListener('click', function() {
        const newText = document.getElementById('edit-textarea').value;
        document.getElementById('story-text').innerHTML = '<p>' + newText.replace(/\n/g, '</p><p>') + '</p>';
        document.getElementById('edit-modal').classList.add('hidden');
    });

    // 取消编辑
    document.querySelector('.modal-cancel').addEventListener('click', function() {
        document.getElementById('edit-modal').classList.add('hidden');
    });

    // 故事标签切换
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const tabContent = {
                'original': '我睡到自然醒，洗漱、吃饭、收拾屋子...',
                'polished': '我睡到自然醒，洗漱、吃饭、收拾屋子，像是在与日常做一个不声张的交易...',
                'wechat': '🌅 今日感悟：慢下来，感受生活的美好...',
                'xiaohongshu': '✨ 今日份治愈 | 慢生活的艺术...'
            };
            
            document.querySelector('.highlight-text').textContent = 
                this.dataset.tab === 'wechat' ? '💫 朋友圈分享' :
                this.dataset.tab === 'xiaohongshu' ? '📕 小红书风格' :
                '成本300 💰 盲审被推荐为校优的毕设';
            
            document.getElementById('story-text').innerHTML = 
                '<p>' + tabContent[this.dataset.tab] + '</p>';
        });
    });

    // 模板选择
    document.querySelectorAll('.template-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.template-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // 生成故事按钮
    document.getElementById('generate-story-btn').addEventListener('click', function() {
        alert('AI正在生成你的故事漫画，请稍候...');
        setTimeout(() => {
            alert('故事漫画生成成功！');
            showPage('diary-page');
        }, 1500);
    });

    // 开始回忆按钮
    document.getElementById('memories-btn').addEventListener('click', function() {
        alert('AI正在理解你的回忆...');
        setTimeout(() => {
            alert('回忆分析完成！点击「漫画人生」生成漫画');
        }, 1000);
    });

    // 风格选择
    document.getElementById('style-select').addEventListener('change', function() {
        const styles = {
            'default': '默认风格',
            'warm': '温暖治愈风格',
            'cool': '高冷文艺风格',
            'humor': '幽默风趣风格',
            'dramatic': '戏剧张力风格'
        };
        if (this.value !== 'default') {
            alert('已切换至：' + styles[this.value]);
        }
    });

    // 移除图片
    document.querySelectorAll('.remove-img').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.parentElement.remove();
        });
    });

    // 移除选中漫画
    document.querySelectorAll('.remove-selected').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.parentElement.remove();
        });
    });
});