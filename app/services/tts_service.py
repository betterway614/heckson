from pathlib import Path

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from dashscope.audio.tts import SpeechSynthesizer
    import dashscope
    dashscope.api_key = settings.dashscope_api_key
    USE_MOCK = False
except ImportError:
    from app.services.mock_sdk import MockSpeechSynthesizer as SpeechSynthesizer
    USE_MOCK = True


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

        # 保存音频
        output_path = get_output_path(generation_id, "narration.mp3")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        return output_path


# 单例
tts_service = TTSService()
