import os
import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.config import get_settings

settings = get_settings()


def extract_exif_taken_at(file_path: str) -> Optional[datetime]:
    """
    从图片 EXIF 数据中提取拍摄时间

    Returns:
        Optional[datetime]: 拍摄时间，提取失败返回 None
    """
    try:
        from PIL import Image
        from PIL.ExifTags import Base as ExifBase

        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None

            # EXIF Tag 36867 = DateTimeOriginal (拍摄时间)
            # EXIF Tag 306 = DateTime (修改时间)
            date_str = exif_data.get(36867) or exif_data.get(306)
            if not date_str:
                return None

            # EXIF 时间格式: "2024:01:15 10:30:00"
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")

    except Exception:
        return None


async def save_upload_file(file: UploadFile, sub_dir: str = "images") -> tuple[str, str, Optional[datetime]]:
    """
    保存上传文件到本地存储并提取 EXIF 时间

    Returns:
        tuple: (file_path, original_filename, taken_at)
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

    # 提取 EXIF 拍摄时间
    taken_at = extract_exif_taken_at(str(file_path))

    return str(file_path), file.filename, taken_at


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
