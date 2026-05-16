import asyncio
from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_params JSONB;'))
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_script TEXT;'))
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_url VARCHAR(512);'))
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_resolution VARCHAR(32);'))
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_duration INTEGER;'))
        await conn.execute(text('ALTER TABLE generations ADD COLUMN IF NOT EXISTS video_style VARCHAR(32);'))
        print("Columns added successfully")

if __name__ == "__main__":
    asyncio.run(main())