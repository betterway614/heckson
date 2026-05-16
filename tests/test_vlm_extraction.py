"""
VLM 信息提取测试 - 使用测试图片验证 VLM 服务
"""
import asyncio
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vlm_service import vlm_service

# 测试图片路径
TEST_IMAGE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "test_document", "微信图片_20260516165752_154_2786.jpg"
)

# VLM 提示词 - 场景信息提取
VLM_PROMPT_SCENE = """你是一个专业的图片分析助手。请仔细观察这张图片，提取以下信息并以JSON格式返回：

{
  "scene": "场景描述（简短概括）",
  "mood": "氛围/情绪",
  "objects": ["图片中的主要物品列表"],
  "people_count": "人物数量估计",
  "location": "推测的地点类型",
  "time_of_day": "推测的时间段",
  "colors": ["主要颜色"],
  "details": "细节描述（50字以内）"
}

请只返回JSON，不要有其他文字。"""

# VLM 提示词 - 日记风格信息提取
VLM_PROMPT_DIARY = """你是一个日记创作助手，需要从图片中提取可用于创作日记的信息。

请分析这张图片，提取以下信息并以JSON格式返回：

{
  "scene_description": "场景描述（用于日记创作，100字以内）",
  "mood": "整体氛围",
  "key_elements": ["关键元素，可用于创作"],
  "suggested_title": "建议的日记标题",
  "emotion_keywords": ["情绪关键词"],
  "story_hint": "从图片推测的故事线索（50字以内）"
}

请只返回JSON，不要有其他文字。"""


async def test_vlm_extraction():
    """测试 VLM 信息提取"""
    results = {}
    abs_path = os.path.abspath(TEST_IMAGE)

    # 检查图片是否存在
    if not os.path.exists(abs_path):
        print(f"[ERROR] Image not found: {abs_path}")
        return

    print(f"[OK] Image found: {abs_path}")

    # 测试1: 场景信息提取
    print("\n[Test 1] Scene extraction...")
    try:
        result1 = await vlm_service.parse_image(
            image_path=abs_path,
            prompt=VLM_PROMPT_SCENE
        )
        results["scene"] = result1
        has_raw = "raw_text" in result1
        print(f"[OK] Scene extraction - parsed: {not has_raw}")
    except Exception as e:
        print(f"[FAIL] Scene extraction: {e}")

    # 测试2: 日记风格信息提取
    print("[Test 2] Diary extraction...")
    try:
        result2 = await vlm_service.parse_image(
            image_path=abs_path,
            prompt=VLM_PROMPT_DIARY
        )
        results["diary"] = result2
        has_raw = "raw_text" in result2
        print(f"[OK] Diary extraction - parsed: {not has_raw}")
    except Exception as e:
        print(f"[FAIL] Diary extraction: {e}")

    # 测试3: 带用户文字的融合提取
    print("[Test 3] Fusion extraction...")
    user_text = "今天和同事们一起吃披萨，很开心！"
    fusion_prompt = """你是一个日记创作助手。用户提供了图片和一段文字描述。

用户文字: {user_text}

请结合图片内容和用户文字，提取以下信息并以JSON格式返回：

{
  "scene_description": "融合后的场景描述（100字以内）",
  "mood": "整体氛围",
  "user_intent": "用户想要表达的核心意思",
  "enhanced_elements": ["从图片中发现的、可以丰富用户描述的元素"],
  "suggested_title": "建议的日记标题"
}

请只返回JSON，不要有其他文字。"""
    try:
        result3 = await vlm_service.parse_image(
            image_path=abs_path,
            prompt=fusion_prompt,
            user_text=user_text
        )
        results["fusion"] = result3
        has_raw = "raw_text" in result3
        print(f"[OK] Fusion extraction - parsed: {not has_raw}")
    except Exception as e:
        print(f"[FAIL] Fusion extraction: {e}")

    # 将结果写入文件（避免终端编码问题）
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vlm_test_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Results saved to: {output_file}")
    print("[DONE] All tests completed")


if __name__ == "__main__":
    asyncio.run(test_vlm_extraction())
