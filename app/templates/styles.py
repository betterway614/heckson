import yaml
from pathlib import Path
from typing import Optional


class StyleManager:
    """风格模板管理器"""

    def __init__(self):
        self.styles = self._load_styles()

    def _load_styles(self) -> dict:
        """加载风格配置"""
        config_path = Path(__file__).parent / "styles.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("styles", {})

    def get_style(self, key: str) -> Optional[dict]:
        """获取指定风格"""
        return self.styles.get(key)

    def list_styles(self) -> list[dict]:
        """获取所有风格列表"""
        return [
            {
                "key": key,
                "name": style["name"],
                "description": style["description"]
            }
            for key, style in self.styles.items()
        ]

    def render_prompt(self, key: str, **kwargs) -> str:
        """渲染风格提示词"""
        style = self.get_style(key)
        if not style:
            raise ValueError(f"Style not found: {key}")

        template = style.get("llm_prompt", "")
        return template.format(**kwargs)
