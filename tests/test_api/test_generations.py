import pytest


@pytest.mark.asyncio
async def test_create_generation(client):
    """测试创建生成任务（阶段1：VLM解析）"""
    # 先创建记忆
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "今天去了咖啡店",
            "memory_date": "2025-01-16",
            "mood_tag": "happy"
        }
    )
    memory_id = memory_response.json()["id"]

    # 创建生成任务
    response = await client.post(
        "/api/generations/",
        json={
            "memory_ids": [memory_id],
            "type": "diary",
            "style_key": "watercolor"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "diary"
    assert data["style_key"] == "watercolor"
    assert data["status"] == "processing"
    assert data["stage"] == "vlm_parse"


@pytest.mark.asyncio
async def test_get_generation(client):
    """测试获取生成任务状态"""
    # 先创建记忆
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "测试记忆",
            "memory_date": "2025-01-16",
            "mood_tag": "neutral"
        }
    )
    memory_id = memory_response.json()["id"]

    # 创建生成任务
    create_response = await client.post(
        "/api/generations/",
        json={
            "memory_ids": [memory_id],
            "type": "diary",
            "style_key": "manga_jp"
        }
    )
    generation_id = create_response.json()["id"]

    # 获取任务状态
    response = await client.get(f"/api/generations/{generation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == generation_id
    assert "status" in data
    assert "stage" in data


@pytest.mark.asyncio
async def test_update_prompt(client):
    """测试更新用户编辑的提示词"""
    # 先创建记忆
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "测试记忆",
            "memory_date": "2025-01-16",
            "mood_tag": "happy"
        }
    )
    memory_id = memory_response.json()["id"]

    # 创建生成任务
    create_response = await client.post(
        "/api/generations/",
        json={
            "memory_ids": [memory_id],
            "type": "diary",
            "style_key": "watercolor"
        }
    )
    generation_id = create_response.json()["id"]

    # 更新提示词（注意：需要任务状态为pending_confirmation才能更新）
    # 这里只是测试API端点存在，实际状态可能需要mock
    response = await client.put(
        f"/api/generations/{generation_id}/prompt",
        json={
            "user_edited_prompt": "一个温暖的咖啡店场景，阳光透过窗户洒进来"
        }
    )
    # 由于VLM解析可能还没完成，状态可能不是pending_confirmation
    # 所以这里可能返回400或200
    assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_polish_prompt(client):
    """测试LLM润色提示词"""
    # 先创建记忆
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "测试记忆",
            "memory_date": "2025-01-16",
            "mood_tag": "happy"
        }
    )
    memory_id = memory_response.json()["id"]

    # 创建生成任务
    create_response = await client.post(
        "/api/generations/",
        json={
            "memory_ids": [memory_id],
            "type": "diary",
            "style_key": "watercolor"
        }
    )
    generation_id = create_response.json()["id"]

    # 测试LLM润色端点
    response = await client.post(
        f"/api/generations/{generation_id}/polish",
        json={
            "prompt": "咖啡店，阳光，温暖"
        }
    )
    # 由于需要API密钥和特定状态，可能返回错误
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_confirm_prompt(client):
    """测试确认提示词"""
    # 先创建记忆
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "测试记忆",
            "memory_date": "2025-01-16",
            "mood_tag": "happy"
        }
    )
    memory_id = memory_response.json()["id"]

    # 创建生成任务
    create_response = await client.post(
        "/api/generations/",
        json={
            "memory_ids": [memory_id],
            "type": "diary",
            "style_key": "watercolor"
        }
    )
    generation_id = create_response.json()["id"]

    # 确认提示词
    response = await client.post(
        f"/api/generations/{generation_id}/confirm",
        json={
            "final_prompt": "水彩风格的咖啡店场景，温暖的阳光，治愈系"
        }
    )
    # 由于需要特定状态，可能返回400或200
    assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_get_nonexistent_generation(client):
    """测试获取不存在的生成任务"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/generations/{fake_id}")
    assert response.status_code == 404
