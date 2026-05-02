import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

async def test_timeweb():
    load_dotenv()
    api_key = os.getenv("TIMEWEB_API_KEY")
    base_url = os.getenv("TIMEWEB_BASE_URL", "https://api.timeweb.ai/v1")
    
    print(f"Testing Timeweb API...")
    print(f"URL: {base_url}")
    print(f"Key: {api_key[:6]}...{api_key[-4:] if api_key else ''}")
    
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    try:
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print("✅ Success!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Failed!")
        print(f"Error type: {type(e)}")
        print(f"Error message: {e}")

if __name__ == "__main__":
    asyncio.run(test_timeweb())
