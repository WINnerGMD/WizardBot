import json
import time
import os
import secrets
import asyncpg
import datetime
import asyncio

class KeyManager:
    def __init__(self):
        self.pool = None
        self.dsn = os.environ.get("DATABASE_URL", "postgresql://wizard:wizard_password@localhost:5433/wizardbot")

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn)
            await self._init_db()
            await self._migrate_from_json()

    async def _init_db(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    key_string VARCHAR(255) UNIQUE NOT NULL,
                    status VARCHAR(50) DEFAULT 'ACTIVE',
                    unfreeze_time TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP
                )
            ''')

    async def _migrate_from_json(self):
        # Look for keys.json in src/core/ instead of managers/
        keys_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys.json")
        if os.path.exists(keys_file):
            try:
                with open(keys_file, "r") as f:
                    content = f.read().strip()
                    keys_data = json.loads(content) if content else {}
                
                if keys_data:
                    async with self.pool.acquire() as conn:
                        for key_str, unfreeze in keys_data.items():
                            dt = datetime.datetime.fromtimestamp(unfreeze)
                            await conn.execute('''
                                INSERT INTO api_keys (key_string, unfreeze_time) 
                                VALUES ($1, $2)
                                ON CONFLICT (key_string) DO NOTHING
                            ''', key_str, dt)
                # Переименуем, чтобы не парсить дважды
                os.rename(keys_file, keys_file + ".bak")
                print("✅ Ключи успешно мигрированы из JSON в PostgreSQL.")
            except Exception as e:
                print(f"Ошибка миграции JSON: {e}")

    async def get_valid_key(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            # Ищем активный ключ
            row = await conn.fetchrow('''
                SELECT key_string FROM api_keys 
                WHERE (unfreeze_time IS NULL OR unfreeze_time <= NOW())
                AND status != 'BANNED'
                ORDER BY total_requests ASC, last_used_at ASC NULLS FIRST
                LIMIT 1
            ''')
            
            if not row:
                return None
                
            selected_key = row['key_string']
            
            # Обновляем статистику
            await conn.execute('''
                UPDATE api_keys 
                SET last_used_at = NOW(), total_requests = total_requests + 1, status = 'ACTIVE'
                WHERE key_string = $1
            ''', selected_key)
            
            active_count = await conn.fetchval("SELECT COUNT(*) FROM api_keys WHERE (unfreeze_time IS NULL OR unfreeze_time <= NOW()) AND status != 'BANNED'")
            print(f"🔑 Выдан ключ: {selected_key[:6]}... (Доступно: {active_count})")
            return selected_key

    async def add_key(self, key_str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO api_keys (key_string) VALUES ($1)
                ON CONFLICT (key_string) DO NOTHING
            ''', key_str)
            
    async def get_stats(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            total_keys = await conn.fetchval('SELECT COUNT(*) FROM api_keys')
            active_keys = await conn.fetchval("SELECT COUNT(*) FROM api_keys WHERE (unfreeze_time IS NULL OR unfreeze_time <= NOW()) AND status != 'BANNED'")
            banned_keys = await conn.fetchval("SELECT COUNT(*) FROM api_keys WHERE status = 'BANNED'")
            frozen_keys = await conn.fetchval("SELECT COUNT(*) FROM api_keys WHERE unfreeze_time > NOW() AND status != 'BANNED'")
            total_reqs = await conn.fetchval("SELECT SUM(total_requests) FROM api_keys") or 0
            
            return {
                "total_keys": total_keys,
                "active": active_keys,
                "frozen": frozen_keys,
                "banned": banned_keys,
                "total_requests": total_reqs,
                "active_rpm": active_keys * 15 # Предполагаемый RPM
            }

    async def mark_exhausted(self, api_key: str, status: str = 'RATE_LIMITED', cooldown_seconds: int = 300):
        await self.connect()
        async with self.pool.acquire() as conn:
            actual_cooldown = 31536000 if status == 'BANNED' else cooldown_seconds
            await conn.execute('''
                UPDATE api_keys 
                SET status = $2, 
                    unfreeze_time = NOW() + interval '1 second' * $3,
                    last_used_at = NOW()
                WHERE key_string = $1
            ''', api_key, status, actual_cooldown)
            print(f"⚠️ Ключ {api_key[:6]}... заморожен! Причина: {status} на {actual_cooldown}с")
        
        if hasattr(self, 'bot') and self.bot:
            self.bot.dispatch('key_exhausted', api_key, status, actual_cooldown)

    async def get_frozen_keys(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT key_string FROM api_keys WHERE status != 'BANNED' AND unfreeze_time > NOW()")

    async def unfreeze_key(self, key_string):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE api_keys SET unfreeze_time = NOW(), status = 'ACTIVE' WHERE key_string = $1", key_string)
            print(f"🔓 Ключ {key_string[:6]}... досрочно разморожен!")

    async def check_amnesty(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            # Размораживаем те ключи, у которых вышло время
            updated = await conn.execute('''
                UPDATE api_keys 
                SET status = 'ACTIVE', unfreeze_time = NULL 
                WHERE status != 'BANNED' 
                AND status != 'ACTIVE'
                AND unfreeze_time <= NOW()
            ''')
            if updated != 'UPDATE 0':
                print(f"🔓 Авто-амнистия: {updated}")

key_manager = KeyManager()
