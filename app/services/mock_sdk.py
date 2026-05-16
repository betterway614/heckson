"""
Mock SDK for testing without actual Volcengine SDK
"""
import json
from typing import Any


class MockArkClient:
    """Mock Ark Client"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def chat(self):
        return MockChat()

    @property
    def images(self):
        return MockImages()


class MockChat:
    """Mock Chat"""

    @property
    def completions(self):
        return MockCompletions()


class MockCompletions:
    """Mock Completions"""

    def create(self, **kwargs) -> Any:
        """Mock create method"""
        # 返回模拟响应
        return MockResponse(
            choices=[
                MockChoice(
                    message=MockMessage(
                        content=json.dumps({
                            "caption": "测试标题",
                            "scene_description": "测试场景描述",
                            "bubble_text": "测试气泡文字"
                        }, ensure_ascii=False)
                    )
                )
            ]
        )


class MockImages:
    """Mock Images"""

    def generate(self, **kwargs) -> Any:
        """Mock generate method"""
        return MockImageResponse(
            data=[MockImageData(b64_json="base64encodedimagedata")]
        )


class MockResponse:
    def __init__(self, choices):
        self.choices = choices


class MockChoice:
    def __init__(self, message):
        self.message = message


class MockMessage:
    def __init__(self, content):
        self.content = content


class MockImageResponse:
    def __init__(self, data):
        self.data = data


class MockImageData:
    def __init__(self, b64_json):
        self.b64_json = b64_json


class MockMaasService:
    """Mock MaaS Service"""

    def __init__(self, host: str = "", region: str = ""):
        self.host = host
        self.region = region
        self._ak = ""
        self._sk = ""

    def set_ak(self, ak: str):
        self._ak = ak

    def set_sk(self, sk: str):
        self._sk = sk

    @property
    def audio(self):
        return MockAudio()


class MockAudio:
    """Mock Audio"""

    def speech(self, endpoint_id: str, req: dict) -> Any:
        """Mock speech method"""
        return MockSpeechResponse(audio=b"mock audio data")


class MockSpeechResponse:
    def __init__(self, audio: bytes):
        self.audio = audio
