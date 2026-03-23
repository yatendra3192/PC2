"""Run all SQL migrations against the database on startup."""
import asyncio
import os
import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger("pc2.migrate")


async def run_migrations(db_url: str):
    """Execute all migration files in order."""
    db_url = db_url.replace("postgres://", "postgresql://", 1) if db_url.startswith("postgres://") else db_url

    conn = await asyncpg.connect(db_url)
    try:
        # Create migrations tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        # Find migration files
        migrations_dir = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
        if not migrations_dir.is_dir():
            # In Docker, migrations are at /app/migrations
            migrations_dir = Path("/app/migrations")
        if not migrations_dir.is_dir():
            logger.warning(f"No migrations directory found")
            return

        applied = {row["filename"] for row in await conn.fetch("SELECT filename FROM _migrations")}

        sql_files = sorted(migrations_dir.glob("*.sql"))
        for sql_file in sql_files:
            if sql_file.name in applied:
                logger.info(f"Skipping {sql_file.name} (already applied)")
                continue
            logger.info(f"Applying {sql_file.name}...")
            sql = sql_file.read_text()
            try:
                await conn.execute(sql)
                await conn.execute("INSERT INTO _migrations (filename) VALUES ($1)", sql_file.name)
                logger.info(f"Applied {sql_file.name}")
            except Exception as e:
                logger.error(f"Migration {sql_file.name} failed: {e}")
                # Continue with remaining migrations instead of crashing
                continue

        # Seed default admin user if users table is empty
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        if count == 0:
            logger.info("Seeding default admin user...")
            from passlib.context import CryptContext
            pwd = CryptContext(schemes=["bcrypt"]).hash("admin123")
            # Create default client first
            client_id = await conn.fetchval("""
                INSERT INTO clients (name, code) VALUES ('Default', 'default')
                ON CONFLICT (code) DO UPDATE SET name='Default'
                RETURNING id
            """)
            await conn.execute("""
                INSERT INTO users (email, password_hash, full_name, role, client_id)
                VALUES ('admin@iksula.com', $1, 'Admin', 'admin', $2)
                ON CONFLICT (email) DO NOTHING
            """, pwd, client_id)
            logger.info("Default admin created: admin@iksula.com / admin123")
    finally:
        await conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    asyncio.run(run_migrations(db_url))
