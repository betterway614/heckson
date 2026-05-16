import pytest
from datetime import date

from app.models.media import Media


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


@pytest.mark.asyncio
async def test_list_memories_filters_by_date(client):
    """测试按单日筛选记忆"""
    await client.post(
        "/api/memories/",
        json={
            "content_text": "目标日期记忆",
            "memory_date": "2026-05-16",
            "mood_tag": "happy"
        }
    )
    await client.post(
        "/api/memories/",
        json={
            "content_text": "其他日期记忆",
            "memory_date": "2026-05-15",
            "mood_tag": "calm"
        }
    )

    response = await client.get("/api/memories/?date=2026-05-16")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["memories"][0]["content_text"] == "目标日期记忆"


@pytest.mark.asyncio
async def test_list_memories_filters_by_date_range(client):
    """测试按日期范围筛选记忆"""
    await client.post(
        "/api/memories/",
        json={
            "content_text": "范围内记忆",
            "memory_date": "2026-05-16",
            "mood_tag": "happy"
        }
    )
    await client.post(
        "/api/memories/",
        json={
            "content_text": "范围外记忆",
            "memory_date": "2026-05-12",
            "mood_tag": "calm"
        }
    )

    response = await client.get("/api/memories/?start_date=2026-05-15&end_date=2026-05-17")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["memories"][0]["content_text"] == "范围内记忆"


@pytest.mark.asyncio
async def test_get_memory_media(client, db_session):
    """测试获取记忆关联媒体"""
    memory_response = await client.post(
        "/api/memories/",
        json={
            "content_text": "带图片的记忆",
            "memory_date": "2026-05-16",
            "mood_tag": "happy"
        }
    )
    memory_id = memory_response.json()["id"]
    db_session.add(Media(
        memory_id=memory_id,
        file_path="./uploads/test.jpg",
        file_type="image",
        original_filename="test.jpg",
        sort_order=0
    ))
    await db_session.commit()

    response = await client.get(f"/api/memories/{memory_id}/media")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "test.jpg"
