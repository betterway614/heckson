"""
直接测试图片生成服务
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.img_service import image_service


async def test_image_service():
    """直接测试图片生成服务"""
    print("=" * 60)
    print("  Direct Image Service Test")
    print("=" * 60)

    prompt = "A beautiful watercolor painting of a cozy coffee shop scene, soft warm lighting, artistic style"
    generation_id = "test-direct-001"

    print(f"\nPrompt: {prompt}")
    print(f"Generation ID: {generation_id}")
    print(f"\nCalling image_service.generate_image()...")

    t0 = time.time()
    try:
        image_path = await image_service.generate_image(
            prompt=prompt,
            generation_id=generation_id
        )
        t1 = time.time()

        print(f"\n[OK] Image generated successfully!")
        print(f"  Path: {image_path}")
        print(f"  Time: {t1-t0:.1f}s")

        # 检查文件是否存在
        fs_path = os.path.join("./outputs", image_path)
        if os.path.exists(fs_path):
            file_size = os.path.getsize(fs_path)
            print(f"  File exists: True ({file_size} bytes)")
        else:
            print(f"  File exists: False (checked: {fs_path})")

        return True

    except Exception as e:
        t1 = time.time()
        print(f"\n[FAIL] Image generation failed: {e}")
        print(f"  Time: {t1-t0:.1f}s")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = asyncio.run(test_image_service())
    sys.exit(0 if ok else 1)
