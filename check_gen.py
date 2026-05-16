import asyncio
from app.database import engine
from sqlalchemy import select
from app.models.generation import Generation

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(select(Generation))
        rows = result.all()
        for row in rows:
            print(row.id, row.created_at)

if __name__ == "__main__":
    asyncio.run(main())
