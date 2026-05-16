import os
from pathlib import Path
from http import HTTPStatus
import urllib.request

from app.config import get_settings
from app.utils.file_utils import get_output_path, get_output_filesystem_path

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from dashscope import VideoSynthesis
    import dashscope
    dashscope.api_key = settings.dashscope_api_key
    USE_MOCK = False
except ImportError:
    # 创建 Mock 类
    class MockVideoSynthesis:
        @staticmethod
        def call(**kwargs):
            class MockResponse:
                status_code = 200
                class output:
                    class results:
                        @staticmethod
                        def __getitem__(index):
                            class Result:
                                url = "http://example.com/mock-video.mp4"
                            return Result()
            return MockResponse()
    VideoSynthesis = MockVideoSynthesis
    USE_MOCK = True


class VideoService:
    """视频生成服务"""

    def __init__(self):
        self.model = settings.video_model

    async def generate_video(
        self,
        prompt: str,
        resolution: str = "1280x720",
        duration: int = 15,
        generation_id: str = None
    ) -> str:
        """
        生成视频

        Args:
            prompt: 视频生成提示词
            resolution: 分辨率（如 "1280x720"）
            duration: 时长（秒）
            generation_id: 生成任务 ID

        Returns:
            str: 视频文件路径
        """
        # 调用视频生成
        response = VideoSynthesis.call(
            model=self.model,
            prompt=prompt,
            size=resolution,
            duration=duration
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"视频生成失败: {response.code} - {response.message}")

        # 获取视频URL并下载
        video_url = response.output.results[0].url

        # 保存视频 - 使用文件系统路径写入，返回相对路径用于数据库存储
        fs_path = get_output_filesystem_path(generation_id, "video.mp4")
        Path(fs_path).parent.mkdir(parents=True, exist_ok=True)

        # 下载视频
        urllib.request.urlretrieve(video_url, fs_path)

        # 返回 URL 友好的相对路径
        return get_output_path(generation_id, "video.mp4")


# 单例
video_service = VideoService()
