#!/usr/bin/env python3
"""
验证项目结构和代码正确性
"""
import sys
import importlib

def check_module(module_name):
    """检查模块是否可以导入"""
    try:
        importlib.import_module(module_name)
        print(f"[OK] {module_name}")
        return True
    except ImportError as e:
        print(f"[FAIL] {module_name}: {e}")
        return False
    except Exception as e:
        print(f"[WARN] {module_name}: {e}")
        return False

def main():
    print("=" * 50)
    print("YOU TIME Backend Structure Verification")
    print("=" * 50)

    modules = [
        "app.config",
        "app.database",
        "app.models",
        "app.schemas",
        "app.api",
        "app.services",
        "app.workflows",
        "app.templates",
        "app.utils",
        "app.main",
    ]

    results = []
    for module in modules:
        results.append(check_module(module))

    print("=" * 50)
    print(f"Result: {sum(results)}/{len(results)} modules can be imported")

    if all(results):
        print("[SUCCESS] All modules structure correct!")
        return 0
    else:
        print("[FAILED] Some modules have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
