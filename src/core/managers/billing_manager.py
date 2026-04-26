from src.core.managers.key_manager import key_manager

class BillingManager:
    async def init_db(self):
        async with key_manager.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_users (
                    discord_id BIGINT PRIMARY KEY,
                    tokens BIGINT DEFAULT 0,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    discord_id BIGINT,
                    role VARCHAR(20),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    async def get_user(self, discord_id: int):
        async with key_manager.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM bot_users WHERE discord_id = $1", discord_id)
            if not row:
                await conn.execute("INSERT INTO bot_users (discord_id, tokens) VALUES ($1, 0)", discord_id)
                row = await conn.fetchrow("SELECT * FROM bot_users WHERE discord_id = $1", discord_id)
            return dict(row)

    async def add_tokens(self, discord_id: int, amount: int):
        await self.get_user(discord_id) # ensure user exists
        async with key_manager.pool.acquire() as conn:
            await conn.execute("UPDATE bot_users SET tokens = tokens + $1 WHERE discord_id = $2", amount, discord_id)
            
    async def deduct_tokens(self, discord_id: int, amount: int):
        async with key_manager.pool.acquire() as conn:
            await conn.execute("UPDATE bot_users SET tokens = GREATEST(0, tokens - $1) WHERE discord_id = $2", amount, discord_id)

    async def set_admin(self, discord_id: int, is_admin: bool):
        await self.get_user(discord_id)
        async with key_manager.pool.acquire() as conn:
            await conn.execute("UPDATE bot_users SET is_admin = $1 WHERE discord_id = $2", is_admin, discord_id)

    # --- РАБОТА С ИСТОРИЕЙ ---

    async def save_message(self, discord_id: int, role: str, content: str):
        async with key_manager.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO chat_history (discord_id, role, content) VALUES ($1, $2, $3)",
                discord_id, role, content[:2000]
            )
            # Храним только последние 15 сообщений для экономии токенов
            await conn.execute(
                "DELETE FROM chat_history WHERE id IN (SELECT id FROM chat_history WHERE discord_id=$1 ORDER BY created_at DESC OFFSET 15)",
                discord_id
            )

    async def get_history(self, discord_id: int):
        async with key_manager.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, content FROM chat_history WHERE discord_id=$1 ORDER BY created_at ASC",
                discord_id
            )
            return [{"role": r['role'], "content": r['content']} for r in rows]

billing_manager = BillingManager()
