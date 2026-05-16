"""
ASR服务Mock冒烟测试脚本
独立运行，不依赖数据库
"""
import sys
import os
import asyncio
import tempfile

# 设置测试环境
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///test.db'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch


def run_tests():
    print('=== ASR Mock Smoke Test ===\n')

    # 1. Test Mock Recognition
    from app.services.mock_sdk import MockRecognition
    mock = MockRecognition()
    result = mock.call(model='paraformer-v2', file_urls=['test.wav'])
    assert result.status_code == 200
    assert 'sentence' in result.output
    print('[PASS] Mock Recognition call')

    # 2. Test response structure
    sentence = result.output['sentence'][0]
    assert 'text' in sentence
    assert 'begin_time' in sentence
    assert 'end_time' in sentence
    print('[PASS] Mock response structure')

    # 3. Test config
    from app.config import get_settings, AVAILABLE_MODELS
    settings = get_settings()
    assert settings.asr_model == 'paraformer-v2'
    print(f'[PASS] ASR config: {settings.asr_model}')

    # 4. Test available models
    assert 'asr' in AVAILABLE_MODELS
    assert 'paraformer-v2' in AVAILABLE_MODELS['asr']
    print(f'[PASS] Available ASR models: {list(AVAILABLE_MODELS["asr"].keys())}')

    # 5. Test model registry
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

    # 6. Test ASR service (with mock)
    with patch('app.services.asr_service.USE_MOCK', True):
        with patch('app.services.asr_service.Recognition', MockRecognition):
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

    # 7. Test file not found error
    try:
        asyncio.run(service.transcribe('/nonexistent/file.wav'))
        assert False, 'Should raise exception'
    except FileNotFoundError as e:
        print('[PASS] File not found error handling')

    print('\n=== All tests passed! ===')


if __name__ == '__main__':
    run_tests()
