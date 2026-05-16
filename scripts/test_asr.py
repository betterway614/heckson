"""
ASR服务冒烟测试脚本
独立运行，不依赖数据库
"""
import sys
import os
import asyncio
import tempfile
from unittest.mock import patch, MagicMock

# 设置测试环境
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///test.db'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_mock_recognition_result():
    """创建模拟的 Recognition 返回结果"""
    mock_result = MagicMock()
    mock_result.status_code = 200
    mock_result.output = {
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
    return mock_result


def run_tests():
    print('=== ASR Smoke Test ===\n')

    # 1. Test config
    from app.config import get_settings, AVAILABLE_MODELS
    settings = get_settings()
    assert settings.asr_model == 'paraformer-v2'
    print(f'[PASS] ASR config: {settings.asr_model}')

    # 2. Test available models
    assert 'asr' in AVAILABLE_MODELS
    assert 'paraformer-v2' in AVAILABLE_MODELS['asr']
    print(f'[PASS] Available ASR models: {list(AVAILABLE_MODELS["asr"].keys())}')

    # 3. Test model registry
    from app.models.model_registry import ModelTask, get_model_registry
    assert ModelTask.SPEECH_RECOGNITION.value == 'asr'
    print('[PASS] ASR task type')

    registry = get_model_registry()
    model = registry.get_asr_model()
    assert model == 'paraformer-v2'
    print(f'[PASS] Registry ASR model: {model}')

    config = registry.get_model_config(ModelTask.SPEECH_RECOGNITION)
    assert config.model_type == 'asr'
    assert config.model_name == 'paraformer-v2'
    print(f'[PASS] ASR model config: type={config.model_type}, model={config.model_name}')

    # 4. Test ASR service (with mock)
    mock_result = create_mock_recognition_result()

    with patch('app.services.asr_service.Recognition') as MockRecognition:
        MockRecognition.return_value.call.return_value = mock_result

        from app.services.asr_service import ASRService
        service = ASRService()

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b'mock audio')
            tmp_path = f.name

        try:
            result = asyncio.run(service.transcribe(tmp_path))
            assert isinstance(result, str)
            assert len(result) > 0
            print(f'[PASS] ASR transcribe: {result}')

            result = asyncio.run(service.transcribe_with_timestamps(tmp_path))
            assert isinstance(result, list)
            assert len(result) > 0
            print(f'[PASS] ASR transcribe with timestamps: {len(result)} records')
        finally:
            os.unlink(tmp_path)

    # 5. Test file not found error
    try:
        asyncio.run(service.transcribe('/nonexistent/file.wav'))
        assert False, 'Should raise exception'
    except FileNotFoundError as e:
        print('[PASS] File not found error handling')

    print('\n=== All tests passed! ===')


if __name__ == '__main__':
    run_tests()
