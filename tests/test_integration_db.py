"""
数据库集成冒烟测试

完整链路：创建用户 → 创建Memory → 上传Media → 创建Generation → VLM解析 → 验证入库
"""
import asyncio
import os
import sys
import time
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.database import engine, async_session, init_db
from app.models.user import User
from app.models.memory import Memory
from app.models.media import Media
from app.models.generation import Generation
from app.models.output import Output
from app.utils.file_utils import extract_exif_taken_at
from app.workflows.diary import VLMWorkflow


TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "test_document"
)

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


async def ensure_tables():
    """确保所有表存在"""
    print("[Setup] Creating tables if not exist...")
    await init_db()
    print("[Setup] Tables ready.\n")


async def ensure_test_user(db):
    """确保测试用户存在"""
    stmt = select(User).where(User.id == TEST_USER_ID)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=TEST_USER_ID,
            openid="test_openid_001",
            nickname="测试用户",
            avatar="https://example.com/avatar.jpg"
        )
        db.add(user)
        await db.commit()
        print(f"[Setup] Created test user: {TEST_USER_ID}")
    else:
        print(f"[Setup] Test user exists: {TEST_USER_ID}")
    return user


async def integration_test():
    results = {}
    total_start = time.time()

    print("=" * 70)
    print("  Database Integration Smoke Test")
    print("=" * 70)

    # ========================================
    # Step 0: 初始化
    # ========================================
    await ensure_tables()

    async with async_session() as db:
        await ensure_test_user(db)

        # ========================================
        # Step 1: 创建 Memory (用户输入)
        # ========================================
        print("\n[Step 1] Creating Memory (user input)")
        memory = Memory(
            user_id=TEST_USER_ID,
            content_text="比赛的提供方的达美乐，吃的好饱。",
            memory_date=date(2026, 5, 16),
            mood_tag="happy"
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        print(f"  Memory ID: {memory.id}")
        print(f"  Content: {memory.content_text}")
        print(f"  Date: {memory.memory_date}")
        print(f"  Mood: {memory.mood_tag}")
        results["memory"] = {
            "id": str(memory.id),
            "content_text": memory.content_text,
            "memory_date": str(memory.memory_date),
            "mood_tag": memory.mood_tag
        }

        # ========================================
        # Step 2: 上传 Media (图片，带 EXIF 和 sort_order)
        # ========================================
        print("\n[Step 2] Creating Media records (with EXIF + sort_order)")
        image_files = sorted([
            f for f in os.listdir(TEST_DIR)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])

        media_records = []
        for i, fname in enumerate(image_files):
            abs_path = os.path.abspath(os.path.join(TEST_DIR, fname))
            taken_at = extract_exif_taken_at(abs_path)

            media = Media(
                memory_id=memory.id,
                file_path=abs_path,
                file_type="image",
                original_filename=fname,
                taken_at=taken_at,
                sort_order=i
            )
            db.add(media)
            media_records.append(media)
            print(f"  [{i}] {fname}")
            print(f"      taken_at: {taken_at}")
            print(f"      sort_order: {i}")

        await db.commit()
        for m in media_records:
            await db.refresh(m)

        print(f"\n  Total media created: {len(media_records)}")
        results["media"] = [{
            "id": str(m.id),
            "file": m.original_filename,
            "taken_at": str(m.taken_at),
            "sort_order": m.sort_order
        } for m in media_records]

        # ========================================
        # Step 3: 创建 Generation (生成任务)
        # ========================================
        print("\n[Step 3] Creating Generation (task)")
        generation = Generation(
            user_id=TEST_USER_ID,
            memory_ids=[str(memory.id)],
            type="diary",
            style_key="watercolor",
            status="processing",
            stage="vlm_parse"
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        print(f"  Generation ID: {generation.id}")
        print(f"  Style: {generation.style_key}")
        print(f"  Status: {generation.status}")
        results["generation"] = {
            "id": str(generation.id),
            "style_key": generation.style_key,
            "status": generation.status
        }

        # ========================================
        # Step 4: 运行 VLM 工作流
        # ========================================
        print("\n[Step 4] Running VLM Workflow (VLM extract + LLM diary)")
        t0 = time.time()
        try:
            workflow = VLMWorkflow(db, generation)
            workflow_result = await workflow.run()
            t1 = time.time()

            await db.refresh(generation)
            print(f"  [OK] Workflow completed in {t1-t0:.1f}s")
            print(f"  Status: {generation.status}")
            print(f"  vlm_raw_metadata type: {type(generation.vlm_raw_metadata)}")
            print(f"  user_edited_prompt length: {len(generation.user_edited_prompt or '')} chars")

            if generation.user_edited_prompt:
                print(f"\n  Generated Diary:")
                print(f"  ---")
                print(f"  {generation.user_edited_prompt}")
                print(f"  ---")

            results["workflow"] = {
                "status": generation.status,
                "time_seconds": round(t1 - t0, 1),
                "vlm_raw_metadata": generation.vlm_raw_metadata,
                "diary": generation.user_edited_prompt,
                "diary_length": len(generation.user_edited_prompt or "")
            }
        except Exception as e:
            print(f"  [FAIL] Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        # ========================================
        # Step 5: 验证数据库状态
        # ========================================
        print("\n[Step 5] Verifying database state")

        # 验证 Memory
        stmt_mem = select(Memory).where(Memory.id == memory.id)
        result_mem = await db.execute(stmt_mem)
        db_memory = result_mem.scalar_one()
        print(f"  Memory exists: {db_memory is not None}")
        print(f"  Memory.content_text: {db_memory.content_text}")

        # 验证 Media 数量
        stmt_media = select(Media).where(Media.memory_id == memory.id)
        result_media = await db.execute(stmt_media)
        db_media = result_media.scalars().all()
        print(f"  Media count: {len(db_media)} (expected: {len(image_files)})")
        for m in db_media:
            print(f"    [{m.sort_order}] {m.original_filename} | taken_at={m.taken_at}")

        # 验证 Generation
        stmt_gen = select(Generation).where(Generation.id == generation.id)
        result_gen = await db.execute(stmt_gen)
        db_gen = result_gen.scalar_one()
        print(f"  Generation.status: {db_gen.status}")
        print(f"  Generation.vlm_raw_metadata: {'exists' if db_gen.vlm_raw_metadata else 'empty'}")
        print(f"  Generation.user_edited_prompt: {'exists' if db_gen.user_edited_prompt else 'empty'}")

        results["verification"] = {
            "memory_exists": db_memory is not None,
            "media_count": len(db_media),
            "media_expected": len(image_files),
            "generation_status": db_gen.status,
            "vlm_metadata_exists": db_gen.vlm_raw_metadata is not None,
            "diary_exists": db_gen.user_edited_prompt is not None
        }

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - total_start
    print(f"\n{'=' * 70}")
    all_passed = (
        results["verification"]["memory_exists"] and
        results["verification"]["media_count"] == results["verification"]["media_expected"] and
        results["verification"]["generation_status"] == "pending_confirmation" and
        results["verification"]["vlm_metadata_exists"] and
        results["verification"]["diary_exists"]
    )
    status = "ALL PASSED" if all_passed else "FAILED"
    print(f"  {status}")
    print(f"{'=' * 70}")
    print(f"  Memory created:     {results['verification']['memory_exists']}")
    print(f"  Media uploaded:     {results['verification']['media_count']}/{results['verification']['media_expected']}")
    print(f"  Generation status:  {results['verification']['generation_status']}")
    print(f"  VLM metadata:       {results['verification']['vlm_metadata_exists']}")
    print(f"  Diary generated:    {results['verification']['diary_exists']}")
    print(f"  Total time:         {total_time:.1f}s")
    print(f"{'=' * 70}")

    # Save results
    import json
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "integration_test_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(integration_test())
    sys.exit(0 if ok else 1)
