"""
策略B 日记工作流冒烟测试

测试链路：VLM纯视觉提取 → LLM汇总+用户文本 → 日记正文
不依赖数据库，直接调用服务层。
支持单图和多图测试。
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vlm_service import vlm_service
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager

TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "test_document"
)


async def extract_one_image(abs_path: str, vlm_prompt: str) -> dict:
    """对单张图片做纯视觉提取"""
    result = await vlm_service.parse_image(
        image_path=abs_path,
        prompt=vlm_prompt
    )
    return result


async def smoke_test():
    results = {}
    style_manager = StyleManager()
    vlm_prompt = style_manager.get_vlm_visual_prompt()

    # 发现所有测试图片
    image_files = sorted([
        os.path.join(TEST_DIR, f)
        for f in os.listdir(TEST_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    print("=" * 60)
    print("Strategy B Diary Workflow Smoke Test")
    print("=" * 60)
    print(f"Found {len(image_files)} image(s) in {TEST_DIR}\n")

    if not image_files:
        print("[FAIL] No images found")
        return False

    # ========================================
    # Step 1: VLM Pure Visual Extraction (逐图)
    # ========================================
    print("[Step 1] VLM Pure Visual Extraction (per image, no user text)")
    visual_results = []
    t0 = time.time()

    for i, img_path in enumerate(image_files, 1):
        abs_path = os.path.abspath(img_path)
        fname = os.path.basename(img_path)
        print(f"  Image {i}: {fname}")
        try:
            vr = await extract_one_image(abs_path, vlm_prompt)
            visual_results.append(vr)
            is_parsed = "raw_text" not in vr
            print(f"    [OK] parsed: {is_parsed}")
            if is_parsed:
                print(f"    Scene: {vr.get('scene', 'N/A')}")
                print(f"    Objects: {vr.get('objects', [])}")
                print(f"    People: {vr.get('people', 'N/A')}")
            else:
                print(f"    Raw: {vr.get('raw_text', '')[:80]}...")
        except Exception as e:
            print(f"    [FAIL] {e}")
            return False

    t1 = time.time()
    results["step1_visual"] = visual_results

    # ========================================
    # Step 2: Single-image LLM Aggregation
    # ========================================
    print(f"\n[Step 2] Single-image LLM Aggregation")
    user_text_1 = "今天和同事们一起吃披萨，很开心！"
    print(f"  User text: {user_text_1}")

    t2 = time.time()
    try:
        diary_1 = await llm_service.aggregate_diary(
            visual_results=[visual_results[0]],
            user_text=user_text_1
        )
        t3 = time.time()
        results["step2_single"] = diary_1
        print(f"  [OK] LLM done in {t3-t2:.1f}s")
        print(f"  Diary ({len(diary_1)} chars):")
        print(f"  ---")
        print(f"  {diary_1}")
        print(f"  ---")
    except Exception as e:
        print(f"  [FAIL] LLM aggregation: {e}")
        return False

    # ========================================
    # Step 3: Multi-image LLM Aggregation
    # ========================================
    if len(visual_results) >= 2:
        print(f"\n[Step 3] Multi-image LLM Aggregation ({len(visual_results)} images)")
        user_text_2 = "忙碌的一天，上午在办公室和同事喝咖啡碰杯，中午一起吃披萨，充实！"
        print(f"  User text: {user_text_2}")

        t4 = time.time()
        try:
            diary_2 = await llm_service.aggregate_diary(
                visual_results=visual_results,
                user_text=user_text_2
            )
            t5 = time.time()
            results["step3_multi"] = diary_2
            print(f"  [OK] Multi-image LLM done in {t5-t4:.1f}s")
            print(f"  Diary ({len(diary_2)} chars):")
            print(f"  ---")
            print(f"  {diary_2}")
            print(f"  ---")
        except Exception as e:
            print(f"  [FAIL] Multi-image aggregation: {e}")
            return False
    else:
        t4 = t3
        t5 = t3
        print(f"\n[Step 3] SKIPPED (only {len(visual_results)} image)")

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"ALL PASSED  |  Total: {total_time:.1f}s")
    print(f"  Step 1 (VLM extract): {t1-t0:.1f}s")
    print(f"  Step 2 (Single LLM):  {t3-t2:.1f}s")
    if len(visual_results) >= 2:
        print(f"  Step 3 (Multi LLM):   {t5-t4:.1f}s")
    print(f"{'=' * 60}")

    # Save results
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "smoke_test_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    return True


if __name__ == "__main__":
    ok = asyncio.run(smoke_test())
    sys.exit(0 if ok else 1)
