import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_video_generation_smoke():
    """视频生成完整流程烟雾测试"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 获取视频风格列表
        styles_response = await client.get("/api/generations/video-styles")
        assert styles_response.status_code == 200
        styles = styles_response.json()
        assert "cinematic" in styles

        # 2. 创建视频生成任务
        create_response = await client.post(
            "/api/generations/video",
            json={
                "start_date": "2026-05-01",
                "end_date": "2026-05-16",
                "style": "cinematic",
                "resolution": "1280x720"
            }
        )
        assert create_response.status_code == 200
        generation = create_response.json()
        generation_id = generation["id"]
        assert generation["type"] == "video"
        assert generation["status"] == "processing"

        # 3. 等待脚本生成（轮询状态）
        for _ in range(30):  # 最多等待30秒
            status_response = await client.get(f"/api/generations/{generation_id}")
            status = status_response.json()

            if status["status"] == "pending_confirmation":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Generation failed: {status.get('error_message')}")

            await asyncio.sleep(1)

        # 4. 获取视频脚本
        script_response = await client.get(f"/api/generations/{generation_id}/video-script")
        assert script_response.status_code == 200
        script_data = script_response.json()
        assert script_data["script"] is not None

        # 5. 确认脚本，生成视频
        confirm_response = await client.post(f"/api/generations/{generation_id}/confirm-video")
        assert confirm_response.status_code == 200

        # 6. 等待视频生成
        for _ in range(60):  # 最多等待60秒
            status_response = await client.get(f"/api/generations/{generation_id}")
            status = status_response.json()

            if status["status"] == "done":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Video generation failed: {status.get('error_message')}")

            await asyncio.sleep(1)

        # 7. 验证视频生成完成
        final_status = await client.get(f"/api/generations/{generation_id}")
        final_data = final_status.json()
        assert final_data["status"] == "done"
        assert final_data["video_url"] is not None
