import pytest


@pytest.mark.asyncio
async def test_create_generation(client):
    """测试创建生成任务"""
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
    assert data["status"] == "pending"
