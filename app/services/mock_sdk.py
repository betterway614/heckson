"""
Mock SDK for testing without actual DashScope SDK
"""
import json
from typing import Any
from http import HTTPStatus


class MockGeneration:
    """Mock DashScope Generation"""

    @staticmethod
    def call(**kwargs) -> Any:
        """Mock call method"""
        return MockGenerationResponse(
            status_code=HTTPStatus.OK,
            output=MockGenerationOutput(
                choices=[
                    MockGenerationChoice(
                        message=MockGenerationMessage(
                            content=json.dumps({
                                "caption": "测试标题",
                                "scene_description": "测试场景描述",
                                "bubble_text": "测试气泡文字"
                            }, ensure_ascii=False)
                        )
                    )
                ]
            ),
            usage=MockUsage(total_tokens=100)
        )


class MockAioGeneration:
    """Mock DashScope AioGeneration (异步版本)"""

    @staticmethod
    async def call(**kwargs) -> Any:
        """Mock async call method"""
        return MockGenerationResponse(
            status_code=HTTPStatus.OK,
            output=MockGenerationOutput(
                choices=[
                    MockGenerationChoice(
                        message=MockGenerationMessage(
                            content=json.dumps({
                                "caption": "测试标题",
                                "scene_description": "测试场景描述",
                                "bubble_text": "测试气泡文字"
                            }, ensure_ascii=False)
                        )
                    )
                ]
            ),
            usage=MockUsage(total_tokens=100)
        )


class MockGenerationResponse:
    def __init__(self, status_code, output, usage):
        self.status_code = status_code
        self.output = output
        self.usage = usage
        self.code = None
        self.message = None


class MockGenerationOutput:
    def __init__(self, choices):
        self.choices = choices


class MockGenerationChoice:
    def __init__(self, message):
        self.message = message


class MockGenerationMessage:
    def __init__(self, content):
        self.content = content


class MockUsage:
    def __init__(self, total_tokens):
        self.total_tokens = total_tokens


class MockImageSynthesis:
    """Mock DashScope ImageSynthesis"""

    @staticmethod
    def call(**kwargs) -> Any:
        """Mock call method"""
        return MockImageSynthesisResponse(
            status_code=HTTPStatus.OK,
            output=MockImageSynthesisOutput(
                results=[
                    MockImageSynthesisResult(
                        url="https://example.com/mock-image.png"
                    )
                ]
            )
        )


class MockImageSynthesisResponse:
    def __init__(self, status_code, output):
        self.status_code = status_code
        self.output = output
        self.code = None
        self.message = None


class MockImageSynthesisOutput:
    def __init__(self, results):
        self.results = results
        self.task_status = 'SUCCEEDED'


class MockImageSynthesisResult:
    def __init__(self, url):
        self.url = url


class MockSpeechSynthesizer:
    """Mock DashScope SpeechSynthesizer"""

    @staticmethod
    def call(**kwargs) -> Any:
        """Mock call method"""
        return MockSpeechSynthesizerResponse(
            audio_data=b"mock audio data"
        )


class MockSpeechSynthesizerResponse:
    def __init__(self, audio_data):
        self._audio_data = audio_data

    def get_audio_data(self):
        return self._audio_data

    def get_timestamps(self):
        return []


class MockMultiModalConversation:
    """Mock DashScope MultiModalConversation"""

    @staticmethod
    def call(**kwargs) -> Any:
        """Mock call method"""
        return MockMultiModalResponse(
            status_code=HTTPStatus.OK,
            output=MockMultiModalOutput(
                choices=[
                    MockMultiModalChoice(
                        message=MockMultiModalMessage(
                            content=[{"text": json.dumps({
                                "scene": "公园",
                                "mood": "开心",
                                "objects": ["树", "花", "人"]
                            }, ensure_ascii=False)}]
                        )
                    )
                ]
            )
        )


class MockMultiModalResponse:
    def __init__(self, status_code, output):
        self.status_code = status_code
        self.output = output
        self.code = None
        self.message = None


class MockMultiModalOutput:
    def __init__(self, choices):
        self.choices = choices


class MockMultiModalChoice:
    def __init__(self, message):
        self.message = message


class MockMultiModalMessage:
    def __init__(self, content):
        self.content = content


class MockRecognition:
    """Mock DashScope Recognition (ASR)"""

    def call(self, **kwargs) -> Any:
        """Mock call method"""
        return MockRecognitionResponse(
            status_code=HTTPStatus.OK,
            output={
                "sentence": [
                    {
                        "text": "这是一段测试语音识别结果",
                        "begin_time": 0,
                        "end_time": 5000
                    },
                    {
                        "text": "用于验证ASR服务功能",
                        "begin_time": 5000,
                        "end_time": 10000
                    }
                ]
            }
        )


class MockRecognitionResponse:
    def __init__(self, status_code, output):
        self.status_code = status_code
        self.output = output
        self.code = None
        self.message = None
