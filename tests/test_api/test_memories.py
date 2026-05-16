import pytest
from datetime import date


@pytest.mark.asyncio
async def test_create_memory(client):
    """测试创建记忆"""
    response = await client.post(
        "/api/memories/",
        json={
            "content_text": "今天天气真好",
            "memory_date": str(date.today()),
            "mood_tag": "happy"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content_text"] == "今天天气真好"
    assert data["mood_tag"] == "happy"


@pytest.mark.asyncio
async def test_list_memories(client):
    """测试获取记忆列表"""
    # 先创建一条记忆
    await client.post(
        "/api/memories/",
        json={
            "content_text": "测试记忆",
            "memory_date": str(date.today()),
            "mood_tag": "neutral"
        }
    )

    # 获取列表
    response = await client.get("/api/memories/")
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert data["total"] >= 1
