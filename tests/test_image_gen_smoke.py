"""
图片生成冒烟测试

测试链路：DB读取Generation → 确认prompt → ImageGenWorkflow → 生成图片 → Output入库
"""
import asyncio
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.generation import Generation
from app.models.output import Output
from app.workflows.diary import ImageGenWorkflow


async def image_gen_smoke_test():
    results = {}
    total_start = time.time()

    print("=" * 70)
    print("  Image Generation Smoke Test")
    print("  (DB → Confirm Prompt → Generate Image → Output)")
    print("=" * 70)

    async with async_session() as db:
        # ========================================
        # Step 1: 从数据库读取待确认的 Generation
        # ========================================
        print("\n[Step 1] Reading Generation from DB (pending_confirmation)")
        stmt = (
            select(Generation)
            .where(Generation.status == "pending_confirmation")
            .order_by(Generation.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()

        if not generation:
            print("  [FAIL] No generation with status 'pending_confirmation' found")
            print("  Please run integration test first to create test data")
            return False

        print(f"  Generation ID: {generation.id}")
        print(f"  Style: {generation.style_key}")
        print(f"  Status: {generation.status}")
        print(f"  Has vlm_raw_metadata: {generation.vlm_raw_metadata is not None}")
        print(f"  Has user_edited_prompt: {generation.user_edited_prompt is not None}")

        if generation.user_edited_prompt:
            print(f"\n  Current diary text:")
            print(f"  ---")
            print(f"  {generation.user_edited_prompt}")
            print(f"  ---")

        results["generation"] = {
            "id": str(generation.id),
            "style_key": generation.style_key,
            "status": generation.status,
            "diary_length": len(generation.user_edited_prompt or "")
        }

        # ========================================
        # Step 2: 用户确认提示词 (设置 final_prompt)
        # ========================================
        print("\n[Step 2] Confirming prompt (setting final_prompt)")

        # 使用 user_edited_prompt 作为 final_prompt
        generation.final_prompt = generation.user_edited_prompt
        generation.prompt_confirmed = True
        generation.status = "processing"
        generation.stage = "img_gen"
        await db.commit()
        await db.refresh(generation)

        print(f"  final_prompt set ({len(generation.final_prompt)} chars)")
        print(f"  prompt_confirmed: {generation.prompt_confirmed}")
        print(f"  status: {generation.status}")
        print(f"  stage: {generation.stage}")

        results["prompt_confirm"] = {
            "final_prompt": generation.final_prompt,
            "final_prompt_length": len(generation.final_prompt),
            "status": generation.status
        }

        # ========================================
        # Step 3: 运行 ImageGenWorkflow
        # ========================================
        print("\n[Step 3] Running ImageGenWorkflow")
        print(f"  Style: {generation.style_key}")

        # 先显示将要使用的 img_prompt 模板
        from app.templates.styles import StyleManager
        style_manager = StyleManager()
        style = style_manager.get_style(generation.style_key)
        if style:
            img_prompt_template = style.get("img_prompt", "")
            final_img_prompt = img_prompt_template.format(
                scene_description=generation.final_prompt
            )
            print(f"\n  Image prompt template:")
            print(f"  ---")
            print(f"  {final_img_prompt}")
            print(f"  ---")
            results["img_prompt"] = final_img_prompt

        t0 = time.time()
        try:
            workflow = ImageGenWorkflow(db, generation)
            workflow_result = await workflow.run()
            t1 = time.time()

            await db.refresh(generation)
            print(f"\n  [OK] Workflow completed in {t1-t0:.1f}s")
            print(f"  Status: {generation.status}")
            print(f"  Progress: {generation.progress}%")

            results["workflow"] = {
                "status": generation.status,
                "time_seconds": round(t1 - t0, 1),
                "result": workflow_result
            }
        except Exception as e:
            print(f"\n  [FAIL] Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            generation.status = "failed"
            generation.error_message = str(e)
            await db.commit()
            return False

        # ========================================
        # Step 4: 验证 Output 记录
        # ========================================
        print("\n[Step 4] Verifying Output records")
        stmt_output = (
            select(Output)
            .where(Output.generation_id == generation.id)
            .order_by(Output.created_at.desc())
        )
        result_output = await db.execute(stmt_output)
        outputs = result_output.scalars().all()

        print(f"  Output count: {len(outputs)}")
        for i, output in enumerate(outputs, 1):
            print(f"\n  Output {i}:")
            print(f"    ID: {output.id}")
            print(f"    File path: {output.file_path}")
            print(f"    File type: {output.file_type}")
            print(f"    Metadata: {output.metadata_json}")

            # 检查文件是否存在
            if os.path.exists(output.file_path):
                file_size = os.path.getsize(output.file_path)
                print(f"    File exists: True ({file_size} bytes)")
            else:
                print(f"    File exists: False")

        results["outputs"] = [{
            "id": str(o.id),
            "file_path": o.file_path,
            "file_type": o.file_type,
            "file_exists": os.path.exists(o.file_path),
            "file_size": os.path.getsize(o.file_path) if os.path.exists(o.file_path) else 0,
            "metadata": o.metadata_json
        } for o in outputs]

        # ========================================
        # Step 5: 验证最终状态
        # ========================================
        print("\n[Step 5] Final state verification")
        await db.refresh(generation)
        print(f"  Generation.status: {generation.status}")
        print(f"  Generation.completed_at: {generation.completed_at}")

        results["final_state"] = {
            "status": generation.status,
            "completed_at": str(generation.completed_at) if generation.completed_at else None
        }

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - total_start
    all_passed = (
        len(outputs) > 0 and
        all(os.path.exists(o.file_path) for o in outputs) and
        generation.status == "done"
    )
    status_str = "ALL PASSED" if all_passed else "FAILED"

    print(f"\n{'=' * 70}")
    print(f"  {status_str}")
    print(f"{'=' * 70}")
    print(f"  Generation status:    {generation.status}")
    print(f"  Output count:         {len(outputs)}")
    print(f"  Files generated:      {sum(1 for o in outputs if os.path.exists(o.file_path))}")
    print(f"  Total time:           {total_time:.1f}s")
    print(f"{'=' * 70}")

    # Save results
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "image_gen_smoke_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(image_gen_smoke_test())
    sys.exit(0 if ok else 1)
