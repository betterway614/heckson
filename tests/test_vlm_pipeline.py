"""
VLM 全链路集成测试（走数据库）

测试链路：
1. 创建 Memory + Media 记录
2. 创建 Generation 记录
3. 运行 VLMWorkflow（VLM提取 → LLM汇总）
4. 验证数据正确写入数据库（vlm_raw_metadata, user_edited_prompt, status）
"""
import asyncio
import os
import sys
import json
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.memory import Memory
from app.models.media import Media
from app.models.generation import Generation
from app.workflows.diary import VLMWorkflow

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

TEST_IMAGES = [
    os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "test_document",
        "微信图片_20260516165752_154_2786.jpg"
    )),
    os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "test_document",
        "微信图片_20260516154300_153_2786.jpg"
    )),
]

USER_TEXT = "今天和同事们一起吃披萨，很开心！"


async def run_test():
    print("=" * 70)
    print("  VLM Pipeline Integration Test (with DB)")
    print("=" * 70)

    # ========================================
    # Step 0: 检查测试图片
    # ========================================
    existing_images = [p for p in TEST_IMAGES if os.path.exists(p)]
    if not existing_images:
        print("[FAIL] No test images found in test_document/")
        return False
    print(f"\n[Step 0] Found {len(existing_images)} test image(s)")

    # ========================================
    # Step 1: 创建 Memory + Media
    # ========================================
    print("\n[Step 1] Creating Memory + Media records...")
    memory_id = None

    async with async_session() as db:
        # 确保测试用户存在
        user_stmt = select(User).where(User.id == TEST_USER_ID)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(id=TEST_USER_ID, openid="test_openid", nickname="TestUser")
            db.add(user)
            await db.commit()
            print("  Created test user")

        # 创建 Memory
        memory = Memory(
            id=None,  # auto-generate
            user_id=TEST_USER_ID,
            content_text=USER_TEXT,
            memory_date=date.today(),
        )
        db.add(memory)
        await db.flush()  # 拿到 memory.id

        # 创建 Media
        for idx, img_path in enumerate(existing_images):
            media = Media(
                memory_id=memory.id,
                file_path=img_path,
                file_type="image",
                original_filename=os.path.basename(img_path),
                sort_order=idx,
            )
            db.add(media)

        await db.commit()
        memory_id = memory.id
        print(f"  Memory ID: {memory_id}")
        print(f"  Media count: {len(existing_images)}")
        print(f"  User text: {USER_TEXT}")

    # ========================================
    # Step 2: 创建 Generation
    # ========================================
    print("\n[Step 2] Creating Generation record...")
    generation_id = None

    async with async_session() as db:
        generation = Generation(
            user_id=TEST_USER_ID,
            memory_ids=[str(memory_id)],
            type="diary",
            style_key="watercolor",
            status="processing",
            stage="vlm_parse",
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        generation_id = generation.id
        print(f"  Generation ID: {generation_id}")
        print(f"  Initial status: {generation.status}")

    # ========================================
    # Step 3: 运行 VLMWorkflow（核心测试）
    # ========================================
    print("\n[Step 3] Running VLMWorkflow...")

    async with async_session() as db:
        # 重新加载 generation 到当前会话
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()

        workflow = VLMWorkflow(db, gen)
        try:
            result = await workflow.run()
            print(f"  Workflow completed successfully")
            print(f"  Result keys: {list(result.keys())}")
        except Exception as e:
            print(f"  [FAIL] Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ========================================
    # Step 4: 验证数据库中的数据
    # ========================================
    print("\n[Step 4] Verifying database records...")

    async with async_session() as db:
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()

        # 检查状态
        print(f"  Status: {gen.status}")
        assert gen.status == "pending_confirmation", \
            f"Expected 'pending_confirmation', got '{gen.status}'"
        print(f"  [OK] Status is 'pending_confirmation'")

        # 检查 VLM 原始数据
        vlm_data = gen.vlm_raw_metadata
        assert vlm_data is not None, "vlm_raw_metadata is None"
        assert isinstance(vlm_data, list), f"Expected list, got {type(vlm_data)}"
        assert len(vlm_data) == len(existing_images), \
            f"Expected {len(existing_images)} results, got {len(vlm_data)}"
        print(f"  [OK] vlm_raw_metadata: {len(vlm_data)} image results")

        for i, vr in enumerate(vlm_data):
            print(f"\n  --- Image {i+1} VLM result ---")
            if "raw_text" in vr:
                print(f"    Raw text: {vr['raw_text'][:80]}...")
            else:
                print(f"    Scene: {vr.get('scene', 'N/A')}")
                print(f"    Objects: {vr.get('objects', [])}")
                print(f"    People: {vr.get('people', 'N/A')}")
                print(f"    Environment: {vr.get('environment', 'N/A')}")
            meta = vr.get("_meta", {})
            print(f"    Meta: index={meta.get('index')}, sort_order={meta.get('sort_order')}")

        # 检查日记正文
        diary_text = gen.user_edited_prompt
        assert diary_text is not None, "user_edited_prompt (diary) is None"
        assert len(diary_text) > 10, f"Diary too short: {len(diary_text)} chars"
        print(f"\n  [OK] user_edited_prompt (diary): {len(diary_text)} chars")
        print(f"  ---")
        print(f"  {diary_text}")
        print(f"  ---")

        # 检查进度
        print(f"\n  Progress: {gen.progress}")
        print(f"  Current step: {gen.current_step}")

    # ========================================
    # Summary
    # ========================================
    print(f"\n{'=' * 70}")
    print(f"  ALL CHECKS PASSED")
    print(f"{'=' * 70}")
    print(f"  Memory ID:      {memory_id}")
    print(f"  Generation ID:  {generation_id}")
    print(f"  VLM results:    {len(vlm_data)} images -> DB vlm_raw_metadata")
    print(f"  Diary text:     {len(diary_text)} chars -> DB user_edited_prompt")
    print(f"  Status:         pending_confirmation")
    print(f"{'=' * 70}")

    return True


if __name__ == "__main__":
    ok = asyncio.run(run_test())
    sys.exit(0 if ok else 1)
