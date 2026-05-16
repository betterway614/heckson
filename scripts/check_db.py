#!/usr/bin/env python3
"""
YOU TIME 数据库状态检查脚本

使用方法:
    python scripts/check_db.py

功能:
    1. 检查数据库连接
    2. 检查表是否存在
    3. 显示表结构
    4. 统计记录数
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def check_connection(engine):
    """检查数据库连接"""
    print("\n1. 数据库连接检查")
    print("-" * 40)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"[OK] 连接成功")
            print(f"  PostgreSQL 版本: {version}")
            return True
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        return False


async def check_tables(engine):
    """检查表是否存在"""
    print("\n2. 表结构检查")
    print("-" * 40)

    expected_tables = ['users', 'memories', 'media', 'generations', 'outputs']

    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        existing_tables = [row[0] for row in result]

    for table in expected_tables:
        if table in existing_tables:
            print(f"[OK] {table}")
        else:
            print(f"[FAIL] {table} (不存在)")


async def check_table_structure(engine, table_name):
    """检查表结构"""
    async with engine.connect() as conn:
        result = await conn.execute(text(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """))
        return result.fetchall()


async def check_counts(engine):
    """统计记录数"""
    print("\n3. 数据统计")
    print("-" * 40)

    tables = ['users', 'memories', 'media', 'generations', 'outputs']

    async with engine.connect() as conn:
        for table in tables:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"[OK] {table}: {count} 条记录")
            except Exception as e:
                print(f"[FAIL] {table}: 查询失败 ({e})")


async def show_table_details(engine):
    """显示表详细信息"""
    print("\n4. 表结构详情")
    print("-" * 40)

    tables = ['users', 'memories', 'media', 'generations', 'outputs']

    for table in tables:
        print(f"\n【{table}】")
        try:
            columns = await check_table_structure(engine, table)
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"  {col[0]}: {col[1]} {nullable}{default}")
        except Exception as e:
            print(f"  查询失败: {e}")


async def main():
    """主函数"""
    print("=" * 50)
    print("YOU TIME 数据库状态检查")
    print("=" * 50)

    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    # 检查连接
    if not await check_connection(engine):
        await engine.dispose()
        sys.exit(1)

    # 检查表
    await check_tables(engine)

    # 统计记录数
    await check_counts(engine)

    # 显示表结构详情
    await show_table_details(engine)

    await engine.dispose()

    print("\n" + "=" * 50)
    print("检查完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
