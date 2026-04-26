import asyncio
import os
import asyncpg
from google import genai

async def main():
    dsn = "postgresql://wizard:wizard_password@localhost:5433/wizardbot"
    conn = await asyncpg.connect(dsn)
    
    rows = await conn.fetch("SELECT key_string FROM api_keys WHERE status != 'BANNED' AND (unfreeze_time IS NULL OR unfreeze_time <= NOW())")
    print(f"--- ПРОВЕРКА {len(rows)} КЛЮЧЕЙ ---")
    
    dead_count = 0
    ok_count = 0
    
    for r in rows:
        key = r['key_string']
        client = genai.Client(api_key=key)
        try:
            # Маленький запрос
            await asyncio.to_thread(client.models.generate_content, model="gemini-2.0-flash", contents="Hi", config={"max_output_tokens": 1})
            ok_count += 1
            print(f"✅ {key[:6]} - OK")
        except Exception as e:
            err = str(e).lower()
            if "limit: 0" in err:
                print(f"💀 {key[:6]} - ZERO QUOTA. FREEZING.")
                await conn.execute("UPDATE api_keys SET status = 'DAILY_LIMIT', unfreeze_time = NOW() + interval '24 hours' WHERE key_string = $1", key)
                dead_count += 1
            else:
                print(f"❓ {key[:6]} - WAIT (429/TPM).")
    
    print(f"\nИТОГ: Живых: {ok_count}, Убрано пустышек: {dead_count}")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
