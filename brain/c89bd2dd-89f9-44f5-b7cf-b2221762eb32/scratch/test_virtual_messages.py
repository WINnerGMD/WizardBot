import asyncio
from tests.virtual_field import VirtualField

async def test_messages():
    field = VirtualField()
    
    # Simulate AI calling tools
    print("--- Simulating message tools ---")
    await field.execute_tool("send_webhook_message", {
        "channel_name": "general",
        "content": "Hello world!"
    })
    
    await field.execute_tool("send_embed_message", {
        "channel_name": "general",
        "title": "Welcome",
        "description": "Glad to see you here!"
    })
    
    print("\n--- Checking stored messages ---")
    for i, m in enumerate(field.messages):
        print(f"Message {i+1}:")
        print(f"  Channel: {m.channel_name}")
        print(f"  Content: {m.content}")
        print(f"  Is Embed: {m.is_embed}")

if __name__ == "__main__":
    asyncio.run(test_messages())
