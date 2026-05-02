import os
import asyncio
import httpx
from dotenv import load_dotenv

async def check_models():
    load_dotenv()
    api_key = os.getenv("TIMEWEB_API_KEY")
    url = "https://api.timeweb.ai/v1/models"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_models())
