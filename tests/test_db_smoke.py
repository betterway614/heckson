"""
入库冒烟测试 - 完整链路验证

测试链路：
1. 同步表结构（添加缺失列）
2. 插入测试数据（user + memory + media）
3. 运行 VLMWorkflow（策略B：VLM提取 → LLM汇总）
4. 验证数据库中数据持久化
5. 清理测试数据
"""
import asyncio
import json
import os
import sys
import time
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, async_session, init_db
from app.models.memory import Memory
from app.models.media import Media
from app.models.generation import Generation
from app.workflows.diary import VLMWorkflow

TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "test_document"
)

# 测试用固定 user_id（复用已有的）
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


async def ensure_schema():
    """确保表结构与 model 同步"""
    print("[Setup] Syncing schema...")
    async with engine.begin() as conn:
        # 添加缺失的列
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS taken_at TIMESTAMP"))
        print("  [OK] media.sort_order and media.taken_at ensured")
    print()


async def insert_test_data(session: AsyncSession) -> tuple:
    """插入测试数据，返回 (memory, media_list)"""
    print("[Setup] Cleaning previous test data...")
    await session.execute(text("DELETE FROM outputs WHERE generation_id = '33333333-3333-3333-3333-333333333333'"))
    await session.execute(text("DELETE FROM generations WHERE id = '33333333-3333-3333-3333-333333333333'"))
    await session.execute(text("DELETE FROM media WHERE memory_id = '11111111-1111-1111-1111-111111111111'"))
    await session.execute(text("DELETE FROM memories WHERE id = '11111111-1111-1111-1111-111111111111'"))
    await session.commit()
    print("  [OK] Cleaned")

    print("[Setup] Inserting test data...")

    # 创建 Memory（模拟用户上传的文字 + 关联图片）
    memory = Memory(
        id="11111111-1111-1111-1111-111111111111",
        user_id=TEST_USER_ID,
        content_text="今天和同事们一起吃披萨，很开心！",
        memory_date=date(2026, 5, 16),
        mood_tag="happy"
    )
    session.add(memory)

    # 发现测试图片
    image_files = sorted([
        f for f in os.listdir(TEST_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    media_list = []
    for i, fname in enumerate(image_files):
        abs_path = os.path.abspath(os.path.join(TEST_DIR, fname))
        media = Media(
            id=f"22222222-2222-2222-2222-{str(i).zfill(12)}",
            memory_id=memory.id,
            file_path=abs_path,
            file_type="image",
            original_filename=fname,
            sort_order=i
        )
        session.add(media)
        media_list.append(media)
        print(f"  Media {i}: {fname} (sort_order={i})")

    # 创建 Generation
    generation = Generation(
        id="33333333-3333-3333-3333-333333333333",
        user_id=TEST_USER_ID,
        memory_ids=[str(memory.id)],
        type="diary",
        style_key="watercolor",
        status="processing",
        stage="vlm_extract"
    )
    session.add(generation)

    await session.commit()
    print(f"  [OK] Memory: {memory.id}")
    print(f"  [OK] Media: {len(media_list)} files")
    print(f"  [OK] Generation: {generation.id}")
    print()

    return memory, media_list, generation


async def run_workflow(session: AsyncSession, generation: Generation) -> dict:
    """运行 VLMWorkflow"""
    print("[Workflow] Running VLMWorkflow (Strategy B)...")
    t0 = time.time()

    workflow = VLMWorkflow(session, generation)
    result = await workflow.run()

    t1 = time.time()
    print(f"  [OK] Workflow completed in {t1-t0:.1f}s")
    print(f"  Status: {generation.status}")
    print(f"  Stage: {generation.stage}")
    print(f"  Progress: {generation.progress}%")
    print()

    return result


async def verify_persistence(session: AsyncSession, generation_id: str):
    """验证数据库中的数据"""
    print("[Verify] Checking database persistence...")

    # 查 Generation
    await session.rollback()  # 确保从DB读最新
    gen = await session.get(Generation, generation_id)
    if not gen:
        print("  [FAIL] Generation not found in DB!")
        return False

    print(f"  Generation:")
    print(f"    status: {gen.status}")
    print(f"    stage: {gen.stage}")
    print(f"    progress: {gen.progress}")

    # 验证 vlm_raw_metadata
    vlm_data = gen.vlm_raw_metadata
    if vlm_data:
        print(f"    vlm_raw_metadata: {len(vlm_data)} image results")
        for i, vr in enumerate(vlm_data):
            scene = vr.get("scene", "N/A") if isinstance(vr, dict) else "raw"
            safe_scene = str(scene).encode("gbk", errors="replace").decode("gbk")
            print(f"      Image {i+1}: {safe_scene}")
    else:
        print("    vlm_raw_metadata: EMPTY")
        return False

    # 验证 diary_text（存入 user_edited_prompt）
    diary_text = gen.user_edited_prompt
    if diary_text:
        safe_text = diary_text.encode("gbk", errors="replace").decode("gbk")
        print(f"    diary_text: {len(diary_text)} chars")
        print(f"    ---")
        print(f"    {safe_text}")
        print(f"    ---")
    else:
        print("    diary_text: EMPTY")
        return False

    # 查 Memory metadata
    memory_id = gen.memory_ids[0] if gen.memory_ids else None
    if memory_id:
        mem = await session.get(Memory, memory_id)
        if mem:
            safe_ct = (mem.content_text or "").encode("gbk", errors="replace").decode("gbk")
            print(f"  Memory:")
            print(f"    content_text: {safe_ct}")
            print(f"    metadata_json: {'set' if mem.metadata_json else 'null'}")

    print()
    return True


async def cleanup(session: AsyncSession, generation_id: str, memory_id: str):
    """清理测试数据"""
    print("[Cleanup] Removing test data...")
    async with session.begin():
        await session.execute(text(f"DELETE FROM outputs WHERE generation_id = '{generation_id}'"))
        await session.execute(text(f"DELETE FROM generations WHERE id = '{generation_id}'"))
        await session.execute(text(f"DELETE FROM media WHERE memory_id = '{memory_id}'"))
        await session.execute(text(f"DELETE FROM memories WHERE id = '{memory_id}'"))
    print("  [OK] Test data cleaned up")
    print()


async def main():
    print("=" * 70)
    print("  DB Integration Smoke Test")
    print("=" * 70)
    print()

    # 1. 同步表结构
    await ensure_schema()

    async with async_session() as session:
        # 2. 插入测试数据
        memory, media_list, generation = await insert_test_data(session)

        # 3. 运行工作流
        try:
            result = await run_workflow(session, generation)
        except Exception as e:
            print(f"  [FAIL] Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            await cleanup(session, str(generation.id), str(memory.id))
            return False

        # 4. 验证入库
        ok = await verify_persistence(session, str(generation.id))

        # 5. 清理
        await cleanup(session, str(generation.id), str(memory.id))

    if ok:
        print("=" * 70)
        print("  ALL PASSED - Data persisted to PostgreSQL successfully")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  FAILED - Data verification failed")
        print("=" * 70)

    return ok


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
