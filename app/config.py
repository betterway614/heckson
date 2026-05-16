from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/you_time"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 火山引擎Ark SDK
    ark_api_key: str = ""

    # 火山引擎MaaS SDK (TTS)
    volc_accesskey: str = ""
    volc_secretkey: str = ""

    # 豆包模型端点
    doubao_endpoint_id: str = ""
    doubao_vlm_endpoint_id: str = ""
    seedream_endpoint_id: str = ""
    tts_endpoint_id: str = ""

    # 文件存储
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
