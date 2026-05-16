from fastapi import APIRouter, HTTPException

from app.templates.styles import StyleManager

router = APIRouter(prefix="/api/templates", tags=["templates"])

style_manager = StyleManager()


@router.get("/styles")
async def list_styles():
    """获取风格列表"""
    return style_manager.list_styles()


@router.get("/styles/{style_key}")
async def get_style(style_key: str):
    """获取风格详情"""
    style = style_manager.get_style(style_key)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    return style
