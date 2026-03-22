from __future__ import annotations
import asyncpg
from contextlib import asynccontextmanager
from app.config import settings

pool: asyncpg.Pool | None = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)


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
