from pathlib import Path

from dashscope.audio.asr import Recognition
import dashscope

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()
dashscope.api_key = settings.dashscope_api_key


class ASRService:
    """ASR语音识别服务"""

    def __init__(self):
        self.model = settings.asr_model

    async def transcribe(
        self,
        audio_path: str,
        language: str = "zh-CN"
    ) -> str:
        """
        识别音频文件中的语音

        Args:
            audio_path: 音频文件路径
            language: 语言代码，默认中文

        Returns:
            str: 识别出的文本
        """
        # 检查文件是否存在
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 调用ASR API
        recognition = Recognition()
        result = recognition.call(
            model=self.model,
            file_urls=[audio_path],
            language_hints=[language]
        )

        # 获取识别结果
        if result and hasattr(result, 'output') and result.output:
            # 合并所有识别结果
            texts = []
            for sentence in result.output.get('sentence', []):
                if 'text' in sentence:
                    texts.append(sentence['text'])
            return ''.join(texts)

        raise Exception("ASR识别失败: 未获取到识别结果")

    async def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = "zh-CN"
    ) -> list:
        """
        识别音频并返回带时间戳的结果

        Args:
            audio_path: 音频文件路径
            language: 语言代码

        Returns:
            list: 包含时间戳的识别结果列表 [{"text": "...", "start_time": 0, "end_time": 1000}, ...]
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        recognition = Recognition()
        result = recognition.call(
            model=self.model,
            file_urls=[audio_path],
            language_hints=[language]
        )

        if result and hasattr(result, 'output') and result.output:
            sentences = []
            for sentence in result.output.get('sentence', []):
                sentences.append({
                    "text": sentence.get('text', ''),
                    "start_time": sentence.get('begin_time', 0),
                    "end_time": sentence.get('end_time', 0)
                })
            return sentences

        raise Exception("ASR识别失败: 未获取到识别结果")


# 单例
asr_service = ASRService()
