import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


async def save_upload_file(file: UploadFile, sub_dir: str = "images") -> tuple[str, str]:
    """
    保存上传文件到本地存储

    Returns:
        tuple: (file_path, original_filename)
    """
    # 创建目录
    upload_dir = Path(settings.upload_dir) / sub_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    file_ext = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # 保存文件
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return str(file_path), file.filename


def get_output_path(generation_id: str, filename: str) -> str:
    """获取输出文件路径"""
    output_dir = Path(settings.output_dir) / generation_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / filename)


def delete_file(file_path: str) -> bool:
    """删除文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False
