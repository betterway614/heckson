from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://betterway:9a301301@localhost:5432/you_time"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 阿里云百炼平台
    dashscope_api_key: str = ""

    # 模型配置 - 基础模型（向后兼容）
    llm_model: str = "qwen-plus"
    vlm_model: str = "qwen-vl-plus"
    image_model: str = "wanx-v1"
    tts_model: str = "sambert-zhichu-v1"
    asr_model: str = "paraformer-v2"

    # 模型配置 - 功能细分（可选覆盖）
    # LLM模型配置
    llm_script_model: Optional[str] = None        # 文案生成
    llm_polish_model: Optional[str] = None        # 提示词润色
    llm_analysis_model: Optional[str] = None      # 内容分析
    llm_summary_model: Optional[str] = None       # 摘要生成

    # 视频生成配置
    video_model: str = "wan2.7"
    video_default_resolution: str = "1280x720"
    video_default_duration: int = 15
    video_default_style: str = "cinematic"

    # 文件存储
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_llm_model(self, task: str = "default") -> str:
        """获取LLM模型，支持按任务类型选择"""
        task_model_map = {
            "script": self.llm_script_model,
            "polish": self.llm_polish_model,
            "analysis": self.llm_analysis_model,
            "summary": self.llm_summary_model,
        }
        # 优先使用任务特定模型，否则使用基础模型
        return task_model_map.get(task) or self.llm_model


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# 可用模型配置（供参考和验证）
AVAILABLE_MODELS = {
    "llm": {
        "qwen-turbo": {"speed": "fast", "quality": "standard", "cost": "low"},
        "qwen-plus": {"speed": "medium", "quality": "high", "cost": "medium"},
        "qwen-max": {"speed": "slow", "quality": "highest", "cost": "high"},
        "qwen-max-longcontext": {"speed": "slow", "quality": "highest", "cost": "high", "context": "long"},
    },
    "vlm": {
        "qwen-vl-plus": {"speed": "medium", "quality": "high", "cost": "medium"},
        "qwen-vl-max": {"speed": "slow", "quality": "highest", "cost": "high"},
    },
    "image": {
        "wanx-v1": {"type": "standard"},
        "wanx-v2": {"type": "enhanced"},
    },
    "tts": {
        "sambert-zhichu-v1": {"voice": "zhichu"},
        "sambert-zhiyuan-v1": {"voice": "zhiyuan"},
    },
    "asr": {
        "paraformer-v2": {"type": "realtime", "language": "zh-CN"},
        "paraformer-v1": {"type": "file", "language": "zh-CN"},
    }
}


def get_model_info(model_type: str, model_name: str) -> Optional[Dict]:
    """获取模型信息"""
    return AVAILABLE_MODELS.get(model_type, {}).get(model_name)
