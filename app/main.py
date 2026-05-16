from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.api import memories, media, generations, templates
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="YOU TIME API",
    description="AI人生放映厅后端API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(memories.router)
app.include_router(media.router)
app.include_router(generations.router)
app.include_router(templates.router)

# 挂载静态文件目录
uploads_path = Path(settings.upload_dir)
outputs_path = Path(settings.output_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
outputs_path.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(outputs_path)), name="outputs")


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    await init_db()


@app.get("/")
async def root():
    return {"message": "YOU TIME API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
