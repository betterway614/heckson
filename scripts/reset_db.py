#!/usr/bin/env python3
"""
YOU TIME 数据库重置脚本

使用方法:
    python scripts/reset_db.py

功能:
    1. 删除所有表
    2. 重新创建所有表
    3. 插入测试数据

警告: 此操作会删除所有数据！
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

# 导入所有模型
from app.models import User, Memory, Media, Generation, Output


async def reset_database():
    """重置数据库"""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    # 确认操作
    print("⚠️  警告：此操作将删除所有数据！")
    confirm = input("是否继续？(y/N): ").strip().lower()

    if confirm != 'y':
        print("操作已取消")
        return

    async with engine.begin() as conn:
        # 删除所有表
        await conn.run_sync(Base.metadata.drop_all)
        print("✓ 所有表已删除")

        # 启用 UUID 扩展
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # 重新创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("✓ 所有表已重新创建")

        # 插入测试用户
        await conn.execute(text("""
            INSERT INTO users (id, openid, nickname)
            VALUES ('00000000-0000-0000-0000-000000000001', 'test_openid_001', '测试用户')
            ON CONFLICT (openid) DO NOTHING
        """))
        print("✓ 测试数据已插入")

    await engine.dispose()


async def main():
    """主函数"""
    print("=" * 50)
    print("YOU TIME 数据库重置")
    print("=" * 50)

    await reset_database()

    print("=" * 50)
    print("数据库重置完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
