from __future__ import annotations
import asyncio
import logging
import asyncpg
from contextlib import asynccontextmanager
from app.config import settings

logger = logging.getLogger("pc2")

pool: asyncpg.Pool | None = None


async def init_db():
    global pool
    for attempt in range(5):
        try:
            pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
            logger.info("Database connected successfully")
            return
        except Exception as e:
            logger.warning(f"DB connection attempt {attempt + 1}/5 failed: {e}")
            if attempt < 4:
                await asyncio.sleep(2)
    logger.error("Could not connect to database after 5 attempts")


async def close_db():
    global pool
    if pool:
        await pool.close()


@asynccontextmanager
async def get_conn():
    async with pool.acquire() as conn:
        yield conn


async def fetch_one(query: str, *args):
    async with get_conn() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args):
    async with get_conn() as conn:
        return await conn.fetch(query, *args)


async def execute(query: str, *args):
    async with get_conn() as conn:
        return await conn.execute(query, *args)


async def execute_returning(query: str, *args):
    async with get_conn() as conn:
        return await conn.fetchrow(query, *args)
