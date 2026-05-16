from pathlib import Path

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()

# 尝试导入真实SDK，如果不可用则使用mock
try:
    from volcengine.maas.v2 import MaasService
    from volcengine.maas import MaasException
    USE_MOCK = False
except ImportError:
    from app.services.mock_sdk import MockMaasService as MaasService
    MaasException = Exception
    USE_MOCK = True


class TTSService:
    """TTS语音合成服务"""

    def __init__(self):
        self.maas = MaasService(
            host='maas-api.ml-platform-cn-beijing.volces.com',
            region='cn-beijing'
        )
        self.maas.set_ak(settings.volc_accesskey)
        self.maas.set_sk(settings.volc_secretkey)
        self.endpoint_id = settings.tts_endpoint_id

    async def synthesize(
        self,
        text: str,
        generation_id: str,
        voice: str = "zh_female_qingxin"
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
        req = {
            "text": text,
            "voice": voice
        }

        try:
            resp = self.maas.audio.speech(self.endpoint_id, req)

            # 保存音频
            output_path = get_output_path(generation_id, "narration.mp3")

            # 确保目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(resp.audio)

            return output_path
        except Exception as e:
            raise Exception(f"TTS合成失败: {str(e)}")


# 单例
tts_service = TTSService()
