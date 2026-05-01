import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_timeweb():
    api_key = os.getenv("TIMEWEB_API_KEY")
    base_url = "https://api.timeweb.ai/v1"
    
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    models_to_test = ["openai/gpt-4o-mini", "deepseek-chat", "deepseek/deepseek-v3", "openai/gpt-4.1"]
    
    for model in models_to_test:
        print(f"\n--- Testing model: {model} ---")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello!"}]
            )
            print(f"Success! Response: {response.choices[0].message.content[:50]}...")
        except Exception as e:
            print(f"Failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_timeweb())
