"""
模型注册表 - 管理不同功能的模型配置

支持：
- 按任务类型选择模型
- 动态模型切换
- 模型能力查询
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from functools import lru_cache

from app.config import get_settings, AVAILABLE_MODELS


class ModelTask(str, Enum):
    """模型任务类型"""
    # LLM任务
    SCRIPT_GENERATION = "script"      # 文案生成
    PROMPT_POLISH = "polish"          # 提示词润色
    CONTENT_ANALYSIS = "analysis"     # 内容分析
    SUMMARY = "summary"               # 摘要生成

    # ASR任务
    SPEECH_RECOGNITION = "asr"        # 语音识别


@dataclass
class ModelConfig:
    """模型配置"""
    model_type: str  # "llm" 或 "vlm"
    task: ModelTask
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1024


class ModelRegistry:
    """模型注册表"""

    def __init__(self):
        self.settings = get_settings()
        self._custom_configs: Dict[str, ModelConfig] = {}

    def get_llm_model(self, task: ModelTask) -> str:
        """获取LLM模型名称"""
        # 检查自定义配置
        if task.value in self._custom_configs:
            config = self._custom_configs[task.value]
            if config.model_type == "llm":
                return config.model_name

        # 使用配置文件中的设置
        return self.settings.get_llm_model(task.value)

    def get_asr_model(self) -> str:
        """获取ASR模型名称"""
        if ModelTask.SPEECH_RECOGNITION.value in self._custom_configs:
            config = self._custom_configs[ModelTask.SPEECH_RECOGNITION.value]
            if config.model_type == "asr":
                return config.model_name
        return self.settings.asr_model

    def get_model_config(self, task: ModelTask) -> Optional[ModelConfig]:
        """获取完整的模型配置"""
        # 检查自定义配置
        if task.value in self._custom_configs:
            return self._custom_configs[task.value]

        # 返回默认配置
        if task in [ModelTask.SCRIPT_GENERATION, ModelTask.PROMPT_POLISH,
                    ModelTask.CONTENT_ANALYSIS, ModelTask.SUMMARY]:
            return ModelConfig(
                model_type="llm",
                task=task,
                model_name=self.get_llm_model(task),
                temperature=0.7,
                max_tokens=1024
            )

        if task == ModelTask.SPEECH_RECOGNITION:
            return ModelConfig(
                model_type="asr",
                task=task,
                model_name=self.get_asr_model(),
                temperature=0.0,
                max_tokens=0
            )

        return None

    def register_model(self, task: ModelTask, config: ModelConfig):
        """注册自定义模型配置"""
        self._custom_configs[task.value] = config

    def unregister_model(self, task: ModelTask):
        """取消自定义模型配置"""
        if task.value in self._custom_configs:
            del self._custom_configs[task.value]

    def get_available_models(self, model_type: str) -> Dict[str, Dict]:
        """获取可用模型列表"""
        return AVAILABLE_MODELS.get(model_type, {})

    def validate_model(self, model_type: str, model_name: str) -> bool:
        """验证模型是否可用"""
        available = self.get_available_models(model_type)
        return model_name in available


@lru_cache()
def get_model_registry() -> ModelRegistry:
    """获取模型注册表单例"""
    return ModelRegistry()


# 预定义的模型配置模板
MODEL_PRESETS = {
    "fast": {
        ModelTask.SCRIPT_GENERATION: ModelConfig("llm", ModelTask.SCRIPT_GENERATION, "qwen-turbo", 0.8, 512),
        ModelTask.PROMPT_POLISH: ModelConfig("llm", ModelTask.PROMPT_POLISH, "qwen-turbo", 0.7, 256),
    },
    "balanced": {
        ModelTask.SCRIPT_GENERATION: ModelConfig("llm", ModelTask.SCRIPT_GENERATION, "qwen-plus", 0.8, 1024),
        ModelTask.PROMPT_POLISH: ModelConfig("llm", ModelTask.PROMPT_POLISH, "qwen-plus", 0.7, 512),
    },
    "quality": {
        ModelTask.SCRIPT_GENERATION: ModelConfig("llm", ModelTask.SCRIPT_GENERATION, "qwen-max", 0.8, 2048),
        ModelTask.PROMPT_POLISH: ModelConfig("llm", ModelTask.PROMPT_POLISH, "qwen-max", 0.7, 1024),
    }
}


def apply_preset(preset_name: str):
    """应用预设模型配置"""
    registry = get_model_registry()

    if preset_name not in MODEL_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(MODEL_PRESETS.keys())}")

    preset = MODEL_PRESETS[preset_name]
    for task, config in preset.items():
        registry.register_model(task, config)