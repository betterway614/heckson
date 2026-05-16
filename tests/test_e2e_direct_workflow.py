"""
端到端测试：直接调用workflow（绕过API异步任务）

测试流程：
1. 创建Memory + Media记录
2. 创建Generation记录
3. 直接运行VLMWorkflow
4. 确认prompt
5. 直接运行ImageGenWorkflow
6. 验证输出文件
"""
import asyncio
import os
import sys
import time
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.memory import Memory
from app.models.media import Media
from app.models.generation import Generation
from app.models.output import Output
from app.workflows.diary import VLMWorkflow, ImageGenWorkflow

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_IMAGE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "test_document",
    "微信图片_20260516165752_154_2786.jpg"
))


async def e2e_direct_workflow_test():
    """端到端测试 - 直接调用workflow"""
    results = {}
    total_start = time.time()

    print("=" * 70)
    print("  E2E Test: Direct Workflow (VLM → Image Gen)")
    print("=" * 70)

    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"[FAIL] Test image not found: {TEST_IMAGE_PATH}")
        return False

    # ========================================
    # Step 1: 创建 Memory + Media
    # ========================================
    print("\n[Step 1] Creating Memory + Media records...")
    memory_id = None
    media_id = None

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
            user_id=TEST_USER_ID,
            content_text="今天和同事们一起吃披萨，很开心！",
            memory_date=date.today()
        )
        db.add(memory)
        await db.flush()

        # 创建 Media - 使用绝对路径
        media = Media(
            memory_id=memory.id,
            file_path=TEST_IMAGE_PATH,
            file_type="image",
            original_filename=os.path.basename(TEST_IMAGE_PATH),
            sort_order=0
        )
        db.add(media)
        await db.commit()

        memory_id = memory.id
        media_id = media.id
        print(f"  Memory ID: {memory_id}")
        print(f"  Media ID: {media_id}")
        print(f"  Image path: {TEST_IMAGE_PATH}")
        results["memory_id"] = str(memory_id)
        results["media_id"] = str(media_id)

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
            stage="vlm_parse"
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        generation_id = generation.id
        print(f"  Generation ID: {generation_id}")
        results["generation_id"] = str(generation_id)

    # ========================================
    # Step 3: 运行 VLMWorkflow
    # ========================================
    print("\n[Step 3] Running VLMWorkflow...")
    t0 = time.time()

    async with async_session() as db:
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()

        workflow = VLMWorkflow(db, gen)
        try:
            vlm_result = await workflow.run()
            t1 = time.time()
            print(f"  [OK] VLM workflow completed in {t1-t0:.1f}s")
            print(f"  Result keys: {list(vlm_result.keys())}")
            results["vlm_time"] = round(t1 - t0, 1)

            # 显示生成的日记
            diary_text = gen.user_edited_prompt
            if diary_text:
                print(f"\n  Generated diary ({len(diary_text)} chars):")
                print(f"  ---")
                print(f"  {diary_text}")
                print(f"  ---")
                results["diary_text"] = diary_text

        except Exception as e:
            t1 = time.time()
            print(f"  [FAIL] VLM workflow failed in {t1-t0:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ========================================
    # Step 4: 确认 Prompt
    # ========================================
    print("\n[Step 4] Confirming prompt...")
    final_prompt = results.get("diary_text", "A beautiful watercolor painting")

    async with async_session() as db:
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()

        gen.final_prompt = final_prompt
        gen.prompt_confirmed = True
        gen.status = "processing"
        gen.stage = "img_gen"
        await db.commit()
        print(f"  Final prompt set ({len(final_prompt)} chars)")
        results["final_prompt"] = final_prompt

    # ========================================
    # Step 5: 运行 ImageGenWorkflow
    # ========================================
    print("\n[Step 5] Running ImageGenWorkflow...")
    t2 = time.time()

    async with async_session() as db:
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()

        workflow = ImageGenWorkflow(db, gen)
        try:
            img_result = await workflow.run()
            t3 = time.time()
            print(f"  [OK] Image generation completed in {t3-t2:.1f}s")
            print(f"  Result: {img_result}")
            results["img_gen_time"] = round(t3 - t2, 1)

        except Exception as e:
            t3 = time.time()
            print(f"  [FAIL] Image generation failed in {t3-t2:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ========================================
    # Step 6: 验证输出
    # ========================================
    print("\n[Step 6] Verifying output...")

    async with async_session() as db:
        # 检查Generation状态
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await db.execute(stmt)
        gen = result.scalar_one()
        print(f"  Generation status: {gen.status}")
        print(f"  Generation progress: {gen.progress}")
        results["final_status"] = gen.status

        # 检查Output记录
        stmt_output = select(Output).where(Output.generation_id == generation_id)
        result_output = await db.execute(stmt_output)
        outputs = result_output.scalars().all()
        print(f"  Output count: {len(outputs)}")

        for i, output in enumerate(outputs, 1):
            print(f"\n  Output {i}:")
            print(f"    ID: {output.id}")
            print(f"    File path: {output.file_path}")
            print(f"    File type: {output.file_type}")

            # 检查文件是否存在
            fs_path = os.path.join("./outputs", output.file_path)
            if os.path.exists(fs_path):
                file_size = os.path.getsize(fs_path)
                print(f"    File exists: True ({file_size} bytes)")
            else:
                print(f"    File exists: False (checked: {fs_path})")

        results["outputs"] = [{
            "id": str(o.id),
            "file_path": o.file_path,
            "file_type": o.file_type
        } for o in outputs]

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - total_start
    all_passed = (
        results.get("memory_id") and
        results.get("vlm_time") and
        results.get("diary_text") and
        results.get("img_gen_time") and
        results.get("final_status") == "done" and
        len(results.get("outputs", [])) > 0
    )
    status_str = "ALL PASSED" if all_passed else "FAILED"

    print(f"\n{'=' * 70}")
    print(f"  {status_str}")
    print(f"{'=' * 70}")
    print(f"  Memory created:       {'Yes' if results.get('memory_id') else 'No'}")
    print(f"  VLM parsed:           {'Yes' if results.get('vlm_time') else 'No'} ({results.get('vlm_time', 0)}s)")
    print(f"  Diary generated:      {'Yes' if results.get('diary_text') else 'No'} ({len(results.get('diary_text', ''))} chars)")
    print(f"  Image generated:      {'Yes' if results.get('img_gen_time') else 'No'} ({results.get('img_gen_time', 0)}s)")
    print(f"  Final status:         {results.get('final_status')}")
    print(f"  Outputs found:        {len(results.get('outputs', []))}")
    print(f"  Total time:           {total_time:.1f}s")
    print(f"{'=' * 70}")

    # Save results
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "e2e_direct_workflow_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(e2e_direct_workflow_test())
    sys.exit(0 if ok else 1)
