import asyncio
import sys
from app.config import config
import asyncpg

ALTERS = [
    "ALTER TABLE tests ALTER COLUMN points_per_correct TYPE REAL USING points_per_correct::REAL;",
    "ALTER TABLE test_results ALTER COLUMN score TYPE REAL USING score::REAL;",
]

async def main():
    try:
        conn = await asyncpg.connect(
            host=config.db.host,
            port=config.db.port,
            database=config.db.database,
            user=config.db.user,
            password=config.db.password
        )
        print(f"Connected to DB {config.db.database} at {config.db.host}:{config.db.port} as {config.db.user}")
        for sql in ALTERS:
            print(f"Executing: {sql}")
            await conn.execute(sql)
            print("OK")
        await conn.close()
        print("All ALTER commands executed successfully.")
    except Exception as e:
        print(f"Migration error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
