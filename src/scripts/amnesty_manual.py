import asyncio
import os
from src.core.key_manager import key_manager

async def unfreeze_all():
    await key_manager.connect()
    async with key_manager.pool.acquire() as conn:
        res = await conn.execute("UPDATE api_keys SET status = 'ACTIVE', unfreeze_time = NULL WHERE status IN ('DAILY_LIMIT', 'RATE_LIMITED');")
        print(f"✅ Результат амнистии: {res}")

if __name__ == "__main__":
    asyncio.run(unfreeze_all())
