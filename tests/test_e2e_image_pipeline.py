"""
端到端测试：图片上传 → 图像输出 完整链路

测试流程：
1. 创建Memory记录
2. 上传图片到Memory
3. 创建Generation任务（触发VLM解析）
4. 等待VLM解析完成
5. 确认prompt
6. 等待图片生成完成
7. 验证输出文件
"""
import asyncio
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.database import async_session
from app.models.memory import Memory
from app.models.media import Media
from app.models.generation import Generation
from app.models.output import Output
from app.main import app
from app.database import get_db
from datetime import date

# 测试图片路径
TEST_IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_document")
TEST_IMAGE_PATH = os.path.join(TEST_IMAGE_DIR, "微信图片_20260516165752_154_2786.jpg")


async def wait_for_generation_status(
    client: AsyncClient,
    generation_id: str,
    target_status: str,
    timeout: int = 120,
    poll_interval: float = 2.0
) -> dict:
    """轮询等待generation达到目标状态"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = await client.get(f"/api/generations/{generation_id}")
        if response.status_code == 200:
            data = response.json()
            current_status = data.get("status")
            print(f"    Status: {current_status} (waiting for {target_status})")
            if current_status == target_status:
                return data
            if current_status == "failed":
                raise Exception(f"Generation failed: {data.get('error_message')}")
        await asyncio.sleep(poll_interval)
    raise TimeoutError(f"Timeout waiting for status {target_status}")


async def e2e_image_pipeline_test():
    """端到端图片生成流水线测试"""
    results = {}
    total_start = time.time()

    print("=" * 70)
    print("  E2E Test: Image Upload → Image Generation Pipeline")
    print("=" * 70)

    # 检查测试图片
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"[FAIL] Test image not found: {TEST_IMAGE_PATH}")
        return False

    async with async_session() as db:
        # 使用ASGI transport测试API
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 覆盖数据库依赖
            async def override_get_db():
                yield db
            app.dependency_overrides[get_db] = override_get_db

            try:
                # ========================================
                # Step 1: 创建Memory
                # ========================================
                print("\n[Step 1] Creating Memory")
                user_id = "00000000-0000-0000-0000-000000000001"
                memory = Memory(
                    user_id=user_id,
                    content_text="测试图片生成流水线",
                    memory_date=date.today()
                )
                db.add(memory)
                await db.commit()
                await db.refresh(memory)
                print(f"  Memory ID: {memory.id}")
                results["memory_id"] = str(memory.id)

                # ========================================
                # Step 2: 上传图片
                # ========================================
                print("\n[Step 2] Uploading image")
                with open(TEST_IMAGE_PATH, "rb") as f:
                    files = {"file": ("test_image.jpg", f, "image/jpeg")}
                    response = await client.post(
                        f"/api/media/upload?memory_id={memory.id}",
                        files=files
                    )

                if response.status_code != 200:
                    print(f"  [FAIL] Upload failed: {response.status_code} - {response.text}")
                    return False

                media_data = response.json()
                print(f"  Media ID: {media_data['id']}")
                print(f"  File path: {media_data['file_path']}")
                results["media"] = media_data

                # ========================================
                # Step 3: 创建Generation任务
                # ========================================
                print("\n[Step 3] Creating Generation task")
                gen_data = {
                    "memory_ids": [str(memory.id)],
                    "type": "diary",
                    "style_key": "watercolor"
                }
                response = await client.post("/api/generations/", json=gen_data)

                if response.status_code != 200:
                    print(f"  [FAIL] Create generation failed: {response.status_code} - {response.text}")
                    return False

                generation_data = response.json()
                generation_id = generation_data["id"]
                print(f"  Generation ID: {generation_id}")
                print(f"  Status: {generation_data['status']}")
                results["generation_id"] = generation_id

                # ========================================
                # Step 4: 等待VLM解析完成
                # ========================================
                print("\n[Step 4] Waiting for VLM parsing (status: pending_confirmation)")
                try:
                    generation_data = await wait_for_generation_status(
                        client, generation_id, "pending_confirmation", timeout=180
                    )
                    print(f"  [OK] VLM parsing completed")
                    print(f"  Stage: {generation_data.get('stage')}")

                    # 获取VLM解析结果
                    vlm_metadata = generation_data.get("vlm_raw_metadata")
                    if vlm_metadata:
                        print(f"  VLM metadata available: {len(str(vlm_metadata))} chars")
                        results["vlm_metadata"] = vlm_metadata

                    user_edited_prompt = generation_data.get("user_edited_prompt")
                    if user_edited_prompt:
                        print(f"  Generated diary text ({len(user_edited_prompt)} chars):")
                        print(f"  ---")
                        print(f"  {user_edited_prompt[:200]}...")
                        print(f"  ---")
                        results["generated_diary"] = user_edited_prompt

                except TimeoutError as e:
                    print(f"  [FAIL] {e}")
                    return False

                # ========================================
                # Step 5: 确认Prompt
                # ========================================
                print("\n[Step 5] Confirming prompt")
                final_prompt = user_edited_prompt or "A beautiful watercolor painting of daily life"
                confirm_data = {
                    "final_prompt": final_prompt,
                    "prompt_confirmed": True
                }
                response = await client.post(
                    f"/api/generations/{generation_id}/confirm",
                    json=confirm_data
                )

                if response.status_code != 200:
                    print(f"  [FAIL] Confirm failed: {response.status_code} - {response.text}")
                    return False

                confirm_result = response.json()
                print(f"  Status: {confirm_result['status']}")
                print(f"  Stage: {confirm_result.get('stage')}")
                results["prompt_confirmed"] = True

                # ========================================
                # Step 6: 等待图片生成完成
                # ========================================
                print("\n[Step 6] Waiting for image generation (status: done)")
                try:
                    generation_data = await wait_for_generation_status(
                        client, generation_id, "done", timeout=300
                    )
                    print(f"  [OK] Image generation completed")
                    print(f"  Progress: {generation_data.get('progress')}%")
                    results["generation_completed"] = True

                except TimeoutError as e:
                    print(f"  [FAIL] {e}")
                    return False

                # ========================================
                # Step 7: 验证输出文件
                # ========================================
                print("\n[Step 7] Verifying output files")
                response = await client.get(f"/api/generations/{generation_id}/outputs")

                if response.status_code != 200:
                    print(f"  [FAIL] Get outputs failed: {response.status_code}")
                    return False

                outputs = response.json()
                print(f"  Output count: {len(outputs)}")

                for i, output in enumerate(outputs, 1):
                    print(f"\n  Output {i}:")
                    print(f"    ID: {output.get('id')}")
                    print(f"    URL: {output.get('url')}")
                    print(f"    File type: {output.get('file_type')}")

                    # 检查文件是否存在
                    file_path = output.get("file_path", "")
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        print(f"    File exists: True ({file_size} bytes)")
                    else:
                        print(f"    File exists: False (path: {file_path})")

                results["outputs"] = outputs

                # ========================================
                # Step 8: 获取完整Generation信息
                # ========================================
                print("\n[Step 8] Final Generation state")
                response = await client.get(f"/api/generations/{generation_id}")
                final_gen = response.json()
                print(f"  Status: {final_gen.get('status')}")
                print(f"  Completed at: {final_gen.get('completed_at')}")
                print(f"  Final prompt length: {len(final_gen.get('final_prompt', ''))}")
                results["final_generation"] = final_gen

            finally:
                app.dependency_overrides.clear()

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - total_start
    all_passed = (
        results.get("memory_id") and
        results.get("media") and
        results.get("generation_id") and
        results.get("vlm_metadata") is not None and
        results.get("prompt_confirmed") and
        results.get("generation_completed") and
        len(results.get("outputs", [])) > 0
    )
    status_str = "ALL PASSED" if all_passed else "FAILED"

    print(f"\n{'=' * 70}")
    print(f"  {status_str}")
    print(f"{'=' * 70}")
    print(f"  Memory created:       {'Yes' if results.get('memory_id') else 'No'}")
    print(f"  Image uploaded:       {'Yes' if results.get('media') else 'No'}")
    print(f"  VLM parsed:           {'Yes' if results.get('vlm_metadata') is not None else 'No'}")
    print(f"  Prompt confirmed:     {'Yes' if results.get('prompt_confirmed') else 'No'}")
    print(f"  Image generated:      {'Yes' if results.get('generation_completed') else 'No'}")
    print(f"  Outputs found:        {len(results.get('outputs', []))}")
    print(f"  Total time:           {total_time:.1f}s")
    print(f"{'=' * 70}")

    # Save results
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "e2e_image_pipeline_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(e2e_image_pipeline_test())
    sys.exit(0 if ok else 1)
