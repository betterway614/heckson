from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api import memories, media, generations, templates

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
