from volcengine.maas.v2 import MaasService
from volcengine.maas import MaasException

from app.config import get_settings
from app.utils.file_utils import get_output_path

settings = get_settings()


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
            with open(output_path, "wb") as f:
                f.write(resp.audio)

            return output_path
        except MaasException as e:
            raise Exception(f"TTS合成失败: {e.message}")


# 单例
tts_service = TTSService()
