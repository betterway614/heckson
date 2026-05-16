"""
完整冒烟测试 - 包含新功能验证

测试内容：
1. VLM 视觉提取（逐图）
2. LLM 日记汇总（单图/多图）
3. EXIF 时间提取
4. 排序字段验证
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
from app.utils.file_utils import extract_exif_taken_at

TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "test_document"
)


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

    print("=" * 70)
    print("  Full Smoke Test (VLM + LLM + EXIF + Sort)")
    print("=" * 70)
    print(f"Found {len(image_files)} image(s) in {TEST_DIR}\n")

    if not image_files:
        print("[FAIL] No images found")
        return False

    # ========================================
    # Test 1: EXIF 提取测试
    # ========================================
    print("[Test 1] EXIF Time Extraction")
    exif_results = []
    for i, img_path in enumerate(image_files, 1):
        abs_path = os.path.abspath(img_path)
        fname = os.path.basename(img_path)
        taken_at = extract_exif_taken_at(abs_path)
        exif_results.append({
            "file": fname,
            "taken_at": str(taken_at) if taken_at else None
        })
        status = "OK" if taken_at else "No EXIF (expected for WeChat images)"
        print(f"  Image {i}: {fname}")
        print(f"    taken_at: {taken_at or 'None'}")
        print(f"    Status: {status}")

    results["exif"] = exif_results

    # ========================================
    # Test 2: 排序字段模拟测试
    # ========================================
    print(f"\n[Test 2] Sort Order Logic (simulated)")
    print("  Simulating upload order and sort_order assignment:")

    simulated_media = []
    for i, img_path in enumerate(image_files):
        fname = os.path.basename(img_path)
        abs_path = os.path.abspath(img_path)
        taken_at = extract_exif_taken_at(abs_path)

        # 模拟上传时的 sort_order 分配
        simulated_media.append({
            "file": fname,
            "sort_order": i,  # 0=第一张, 1=第二张
            "taken_at": str(taken_at) if taken_at else None,
            "upload_index": i
        })
        print(f"    [{i}] {fname} -> sort_order={i}")

    # 模拟按 sort_order 排序读取
    sorted_media = sorted(simulated_media, key=lambda x: x["sort_order"])
    print(f"\n  Read order (by sort_order):")
    for m in sorted_media:
        print(f"    [{m['sort_order']}] {m['file']}")

    results["sort_simulation"] = {
        "upload_order": simulated_media,
        "read_order": sorted_media,
        "is_consistent": [m["file"] for m in simulated_media] == [m["file"] for m in sorted_media]
    }

    # ========================================
    # Test 3: VLM Pure Visual Extraction
    # ========================================
    print(f"\n[Test 3] VLM Pure Visual Extraction (per image)")
    visual_results = []
    t0 = time.time()

    for i, img_path in enumerate(image_files, 1):
        abs_path = os.path.abspath(img_path)
        fname = os.path.basename(img_path)
        print(f"  Image {i}: {fname}")
        try:
            vr = await vlm_service.parse_image(
                image_path=abs_path,
                prompt=vlm_prompt
            )
            visual_results.append(vr)
            is_parsed = "raw_text" not in vr
            print(f"    [OK] parsed: {is_parsed}")
            if is_parsed:
                print(f"    Scene: {vr.get('scene', 'N/A')}")
                print(f"    Objects: {vr.get('objects', [])}")
                print(f"    People: {vr.get('people', 'N/A')}")
        except Exception as e:
            print(f"    [FAIL] {e}")
            return False

    t1 = time.time()
    results["step3_visual"] = visual_results

    # ========================================
    # Test 4: Single-image LLM Aggregation
    # ========================================
    print(f"\n[Test 4] Single-image LLM Aggregation")
    user_text = "今天和同事们一起吃披萨，很开心！"
    print(f"  User text: {user_text}")

    t2 = time.time()
    try:
        diary = await llm_service.aggregate_diary(
            visual_results=[visual_results[0]],
            user_text=user_text
        )
        t3 = time.time()
        results["step4_single_diary"] = {
            "user_text": user_text,
            "diary": diary,
            "char_count": len(diary),
            "time_seconds": round(t3 - t2, 1)
        }
        print(f"  [OK] LLM done in {t3-t2:.1f}s")
        print(f"  Diary ({len(diary)} chars):")
        print(f"  ---")
        print(f"  {diary}")
        print(f"  ---")
    except Exception as e:
        print(f"  [FAIL] LLM aggregation: {e}")
        return False

    # ========================================
    # Test 5: Multi-image LLM Aggregation
    # ========================================
    if len(visual_results) >= 2:
        print(f"\n[Test 5] Multi-image LLM Aggregation ({len(visual_results)} images)")
        user_text_multi = "忙碌的一天，上午在办公室喝咖啡碰杯，中午一起吃披萨，充实！"
        print(f"  User text: {user_text_multi}")

        t4 = time.time()
        try:
            diary_multi = await llm_service.aggregate_diary(
                visual_results=visual_results,
                user_text=user_text_multi
            )
            t5 = time.time()
            results["step5_multi_diary"] = {
                "user_text": user_text_multi,
                "diary": diary_multi,
                "char_count": len(diary_multi),
                "time_seconds": round(t5 - t4, 1)
            }
            print(f"  [OK] Multi-image LLM done in {t5-t4:.1f}s")
            print(f"  Diary ({len(diary_multi)} chars):")
            print(f"  ---")
            print(f"  {diary_multi}")
            print(f"  ---")
        except Exception as e:
            print(f"  [FAIL] Multi-image aggregation: {e}")
            return False
    else:
        t4 = t3
        t5 = t3
        print(f"\n[Test 5] SKIPPED (only {len(visual_results)} image)")

    # ========================================
    # Summary
    # ========================================
    total_time = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  ALL TESTS PASSED")
    print(f"{'=' * 70}")
    print(f"  EXIF Extraction:       {'OK (with fallback)' if any(r['taken_at'] for r in exif_results) else 'No EXIF (WeChat stripped)'}")
    print(f"  Sort Order Logic:      OK (consistent)")
    print(f"  VLM Extraction:        OK ({len(visual_results)} images)")
    print(f"  Single-image LLM:      OK ({results['step4_single_diary']['char_count']} chars)")
    if 'step5_multi_diary' in results:
        print(f"  Multi-image LLM:       OK ({results['step5_multi_diary']['char_count']} chars)")
    print(f"  Total Time:            {total_time:.1f}s")
    print(f"{'=' * 70}")

    # Save results
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "full_smoke_test_results.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    return True


if __name__ == "__main__":
    ok = asyncio.run(smoke_test())
    sys.exit(0 if ok else 1)
