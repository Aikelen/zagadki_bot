import asyncio
import asyncpg
import os

async def create_table():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            score INTEGER
        );
    """)
    print("✅ Таблица создана!")
    await conn.close()

asyncio.run(create_table())
