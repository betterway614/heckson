"""
真实API测试 - 使用test_document目录下的图片
打印所有输入给模型的提示词（包含时间线信息）
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vlm_service import vlm_service
from app.services.llm_service import llm_service
from app.templates.styles import StyleManager


# 测试数据
TEST_IMAGE_DIR = Path(__file__).parent.parent / "test_document"
USER_TEXT = "比赛的提供方的达美乐，吃的好饱。"

# 模拟时间元数据（实际从数据库读取）
MOCK_TIMESTAMPS = [
    {"filename": "微信图片_20260516154300_153_2786.jpg", "taken_at": "2026-05-16T12:30:00"},
    {"filename": "微信图片_20260516165752_154_2786.jpg", "taken_at": "2026-05-16T13:15:00"},
]


async def test_vlm_extraction():
    """测试VLM视觉提取"""
    print("=" * 80)
    print("[Step 1] VLM 纯视觉提取")
    print("=" * 80)

    style_manager = StyleManager()
    vlm_prompt = style_manager.get_vlm_visual_prompt()

    print("\n[OUTPUT] VLM 提示词:")
    print("-" * 40)
    print(vlm_prompt)
    print("-" * 40)

    # 获取测试图片
    images = list(TEST_IMAGE_DIR.glob("*.jpg")) + list(TEST_IMAGE_DIR.glob("*.png"))
    print(f"\n[INFO] 找到 {len(images)} 张图片:")
    for img in images:
        print(f"   - {img.name}")

    # 逐图提取，附带时间元数据
    visual_results = []
    for idx, img_path in enumerate(images):
        print(f"\n[PROCESS] 正在处理图片 {idx+1}: {img_path.name}")
        print(f"   图片路径: file://{img_path}")

        result = await vlm_service.parse_image(
            image_path=str(img_path),
            prompt=vlm_prompt
        )

        # 附带时间元数据
        meta = MOCK_TIMESTAMPS[idx] if idx < len(MOCK_TIMESTAMPS) else {}
        result["_meta"] = {
            "index": idx,
            "taken_at": meta.get("taken_at"),
            "sort_order": idx,
            "filename": img_path.name
        }
        visual_results.append(result)

        print(f"   拍摄时间: {meta.get('taken_at', '未知')}")
        print(f"   VLM 返回结果:")
        print(f"   {json.dumps(result, ensure_ascii=False, indent=2)}")

    return visual_results


async def test_diary_aggregation(visual_results: list):
    """测试日记汇总（带时间信息）"""
    print("\n" + "=" * 80)
    print("[Step 2] LLM 日记汇总（带时间线）")
    print("=" * 80)

    style_manager = StyleManager()

    # 构建 visual_info（包含时间信息）
    visual_parts = []
    for i, vr in enumerate(visual_results, 1):
        meta = vr.get("_meta", {})
        taken_at = meta.get("taken_at")
        time_str = f" (拍摄时间: {taken_at})" if taken_at else ""

        if "raw_text" in vr:
            visual_parts.append(f"图片{i}{time_str}: {vr['raw_text']}")
        else:
            parts = []
            if vr.get("scene"):
                parts.append(f"场景: {vr['scene']}")
            if vr.get("objects"):
                parts.append(f"物品: {', '.join(vr['objects'])}")
            if vr.get("people"):
                parts.append(f"人物: {vr['people']}")
            if vr.get("environment"):
                parts.append(f"环境: {vr['environment']}")
            if vr.get("details"):
                detail_str = vr["details"] if isinstance(vr["details"], str) else ", ".join(vr["details"])
                parts.append(f"细节: {detail_str}")
            if vr.get("text_in_image"):
                parts.append(f"图中文字: {vr['text_in_image']}")
            visual_parts.append(f"图片{i}{time_str}: {'; '.join(parts)}")
    visual_info = "\n".join(visual_parts)

    # 获取汇总提示词
    aggregation_prompt = style_manager.get_aggregation_prompt(visual_info, USER_TEXT)

    print("\n[OUTPUT] LLM 日记汇总提示词:")
    print("-" * 40)
    print("System: 你是一个情感细腻的日记创作助手，擅长将视觉信息与文字融合成自然流畅的第一人称日记。")
    print("\nUser:")
    print(aggregation_prompt)
    print("-" * 40)

    # 调用LLM
    print("\n[WAIT] 正在调用 LLM...")
    diary_text = await llm_service.aggregate_diary(
        visual_results=visual_results,
        user_text=USER_TEXT
    )

    print(f"\n[RESULT] 生成的日记:")
    print("-" * 40)
    print(diary_text)
    print("-" * 40)

    return diary_text


async def test_comic_prompt(diary_text: str, visual_results: list):
    """测试漫画分镜提示词生成（包括时间线风格）"""
    print("\n" + "=" * 80)
    print("[Step 3] 漫画分镜提示词生成")
    print("=" * 80)

    style_manager = StyleManager()

    # 构建时间线信息
    timeline_parts = []
    for i, vr in enumerate(visual_results, 1):
        meta = vr.get("_meta", {})
        taken_at = meta.get("taken_at")
        scene = vr.get("scene", "未知场景")
        if taken_at:
            time_obj = datetime.fromisoformat(taken_at)
            time_display = time_obj.strftime("%H:%M")
            timeline_parts.append(f"{time_display} - {scene}")
    timeline_info = "\n".join(timeline_parts) if timeline_parts else "（无明确时间线）"

    print(f"\n[INFO] 时间线信息:")
    print(timeline_info)

    # 测试三种漫画风格
    styles = [
        ("comic_shuangwen", "热血爽文"),
        ("comic_zhiyu", "治愈温馨"),
        ("comic_timeline", "一天记录（时间线）")
    ]

    for style_key, style_name in styles:
        print(f"\n[STYLE] 风格: {style_name} ({style_key})")
        comic_prompt = style_manager.get_comic_prompt(style_key, diary_text, timeline_info)

        print(f"\n[OUTPUT] LLM 提示词:")
        print("-" * 40)
        print("System: 你是一个顶级的AI生图提示词专家，严格按要求输出中文提示词组合。")
        print("\nUser:")
        print(comic_prompt)
        print("-" * 40)

        # 调用LLM
        print(f"\n[WAIT] 正在调用 LLM...")
        result = await llm_service.generate_comic_prompt(
            diary_text=diary_text,
            style_key=style_key,
            timeline_info=timeline_info
        )

        print(f"\n[RESULT] 生成的漫画提示词:")
        print("-" * 40)
        print(result)
        print("-" * 40)


async def main():
    print("[START] 开始真实API测试（带时间线）")
    print(f"[DIR] 测试图片目录: {TEST_IMAGE_DIR}")
    print(f"[TEXT] 用户文字: {USER_TEXT}")

    try:
        # Step 1: VLM提取
        visual_results = await test_vlm_extraction()

        # Step 2: 日记汇总
        diary_text = await test_diary_aggregation(visual_results)

        # Step 3: 漫画分镜
        await test_comic_prompt(diary_text, visual_results)

        print("\n" + "=" * 80)
        print("[DONE] 测试完成!")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
