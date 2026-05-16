from pathlib import Path

from dashscope.audio.tts import SpeechSynthesizer
import dashscope

from app.config import get_settings
from app.utils.file_utils import get_output_path, get_output_filesystem_path

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


class TTSService:
    """TTS语音合成服务"""

    def __init__(self):
        self.model = settings.tts_model

    async def synthesize(
        self,
        text: str,
        generation_id: str,
        voice: str = "zhichu"
    ) -> str:
        """
        合成语音

        Args:
            text: 要合成的文本
            generation_id: 生成任务ID
            voice: 音色

        Returns:
            str: 生成的音频文件路径
        """
        result = SpeechSynthesizer.call(
            model=self.model,
            text=text,
            format='mp3',
            sample_rate=16000,
            volume=50,
            rate=1.0,
            pitch=1.0
        )

        # 获取音频数据
        audio_data = result.get_audio_data()

        if audio_data is None:
            raise Exception("TTS合成失败: 未获取到音频数据")

        # 保存音频 - 使用文件系统路径写入，返回相对路径用于数据库存储
        fs_path = get_output_filesystem_path(generation_id, "narration.mp3")
        Path(fs_path).parent.mkdir(parents=True, exist_ok=True)

        with open(fs_path, "wb") as f:
            f.write(audio_data)

        # 返回 URL 友好的相对路径
        return get_output_path(generation_id, "narration.mp3")


# 单例
tts_service = TTSService()
