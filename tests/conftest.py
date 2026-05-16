import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.database import Base, get_db
from app.config import get_settings

settings = get_settings()

# 使用配置中的数据库URL，但创建测试数据库
TEST_DATABASE_URL = settings.database_url.replace("you_time", "you_time_test")

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 测试用户ID
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 创建测试用户
        await conn.execute(text(
            f"INSERT INTO users (id, openid, nickname) VALUES ('{TEST_USER_ID}', 'test_openid', 'Test User') ON CONFLICT (id) DO NOTHING"
        ))
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    async with TestSessionLocal() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        app.dependency_overrides.clear()
