import os
import sys
import asyncio

# Setup path so it can import src
sys.path.insert(0, '/Users/nazar/Projects/WizardBot')

from dotenv import load_dotenv
load_dotenv(os.path.join('/Users/nazar/Projects/WizardBot', '.env'))

from src.ai.handlers.timeweb import TimewebHandler
from src.ai.specialists import SPECIALISTS
from src.tools.definitions import TOOLS

async def main():
    handler = TimewebHandler()
    
    # Let's intercept the tool execution so we don't actually delete anything.
    async def mock_execute_tool_logic(name, args, manager, status_callback, usage_context, node_id, depth, user_perms, mode, specialist_name):
        print(f"\n[INTERCEPT] {specialist_name} -> Tool: {name} | Args: {args}")
        if name == "create_pipeline":
            # Show what steps the pipeline has
            steps = args.get("steps", [])
            for i, s in enumerate(steps):
                print(f"  Step {i+1}: {s}")
            return {"content": "Mock pipeline finished", "reports": ["Mock step done"], "success": True}
        if name == "delegate_to_sub_agent":
            return {"content": "Mock delegation finished", "reports": ["Mock delegate done"], "success": True, "is_delegation": True}
        return {"content": f"Mock {name} done", "reports": [f"Mock {name} done"], "success": True}
    
    # Overwrite the execution engine just for test
    handler._execute_tool_logic = mock_execute_tool_logic
    
    prompt = "сделай дискорд сервер для фанатов War Selection предварительно удалив роли старые чтобы с нуля все собирать"
    print(f"Testing Prompt: {prompt}\n")
    
    class MockManager:
        pass
    
    res = await handler._run_agent(
        "orchestrator", 
        prompt, 
        MockManager(), 
        user_perms="administrator",
        depth=0
    )
    print("\nResult:")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
