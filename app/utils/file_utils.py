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
        file_path 返回 URL 友好的相对路径，如 images/uuid.jpg
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

    # 返回 URL 友好的相对路径（不包含 upload_dir 前缀）
    relative_path = f"{sub_dir}/{unique_filename}"
    return relative_path, file.filename, taken_at


def get_output_path(generation_id: str, filename: str) -> str:
    """获取输出文件路径，返回 URL 友好的相对路径"""
    output_dir = Path(settings.output_dir) / generation_id
    output_dir.mkdir(parents=True, exist_ok=True)
    # 返回相对路径，用于数据库存储和 URL 构造
    return f"{generation_id}/{filename}"


def get_output_filesystem_path(generation_id: str, filename: str) -> str:
    """获取输出文件的完整文件系统路径，用于实际文件写入"""
    output_dir = Path(settings.output_dir) / generation_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / filename)


def normalize_file_path(file_path: str, base_dir: str) -> str:
    """将文件路径规范化为 URL 友好的相对路径"""
    # 统一使用正斜杠
    normalized = file_path.replace("\\", "/")

    # 获取 base_dir 的绝对路径形式用于匹配
    base_abs = str(Path(base_dir).resolve()).replace("\\", "/")

    # 情况1：绝对路径 - 去掉 base_dir 前缀
    if normalized.startswith(base_abs):
        relative = normalized[len(base_abs):].lstrip("/")
        return relative

    # 情况2：相对路径带前缀（如 ./uploads/images/xxx.png）
    base_with_dot = f"./{base_dir}/".replace("\\", "/")
    if normalized.startswith(base_with_dot):
        return normalized[len(base_with_dot):]

    # 情况3：直接以 base_dir 开头
    base_prefix = f"{base_dir}/".replace("\\", "/")
    if normalized.startswith(base_prefix):
        return normalized[len(base_prefix):]

    # 已经是相对路径，直接返回
    return normalized


def delete_file(file_path: str) -> bool:
    """删除文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False
