#!/usr/bin/env python3
"""
YOU TIME 数据库初始化脚本

使用方法:
    python scripts/init_db.py

功能:
    1. 创建数据库（如果不存在）
    2. 创建所有表
    3. 插入测试数据
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.database import Base

# 导入所有模型以确保它们被注册到 Base
from app.models import User, Memory, Media, Generation, Output


async def create_database():
    """创建数据库（如果不存在）"""
    settings = get_settings()
    db_url = settings.database_url

    # 提取数据库名称
    db_name = db_url.split("/")[-1]

    # 连接到默认的 postgres 数据库来创建目标数据库
    base_url = db_url.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # 检查数据库是否存在
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name}
        )
        exists = result.scalar()

        if not exists:
            # 创建数据库
            await conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"[OK] 数据库 '{db_name}' 创建成功")
        else:
            print(f"[OK] 数据库 '{db_name}' 已存在")

    await engine.dispose()


async def create_tables():
    """创建所有表"""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        # 启用 UUID 扩展
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("[OK] 所有表创建成功")

    await engine.dispose()


async def insert_test_data():
    """插入测试数据"""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        # 插入测试用户
        await conn.execute(text("""
            INSERT INTO users (id, openid, nickname)
            VALUES ('00000000-0000-0000-0000-000000000001', 'test_openid_001', '测试用户')
            ON CONFLICT (openid) DO NOTHING
        """))
        print("[OK] 测试数据插入成功")

    await engine.dispose()


async def verify_connection():
    """验证数据库连接"""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            print("[OK] 数据库连接验证成功")
            return True
    except Exception as e:
        print(f"[FAIL] 数据库连接失败: {e}")
        return False
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    print("=" * 50)
    print("YOU TIME 数据库初始化")
    print("=" * 50)

    # 先创建数据库（连接到 postgres 数据库）
    await create_database()

    # 验证连接（现在连接到 you_time 数据库）
    if not await verify_connection():
        sys.exit(1)

    # 创建表
    await create_tables()

    # 插入测试数据
    await insert_test_data()

    print("=" * 50)
    print("数据库初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
