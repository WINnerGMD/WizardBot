import asyncio
import os
from src.core.key_manager import key_manager

async def import_from_file(filename="keys.txt"):
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден! Создай его и положи туда ключи.")
        return
        
    with open(filename, "r") as f:
        keys = [line.strip() for line in f if line.strip()]
        
    print(f"📡 Начинаю импорт {len(keys)} ключей...")
    for key in keys:
        try:
            await key_manager.add_key(key)
            print(f"✅ Добавлен: {key[:10]}...")
        except Exception as e:
            print(f"❌ Ошибка для {key[:10]}: {e}")
            
    print("✨ Импорт завершен!")

if __name__ == "__main__":
    asyncio.run(import_from_file())
