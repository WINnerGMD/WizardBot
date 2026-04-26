import asyncio
import json
import uuid
import sys
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load keys
load_dotenv()

@dataclass
class VirtualRole:
    id: int
    name: str
    color: str = "#000000"
    permissions: List[str] = field(default_factory=list)

@dataclass
class VirtualChannel:
    id: int
    name: str
    type: str  # text, voice, category, forum
    category_id: Optional[int] = None
    permissions: List[Dict] = field(default_factory=list)

@dataclass
class VirtualUser:
    id: int
    name: str
    roles: List[int] = field(default_factory=list)

class VirtualField:
    """A simulation environment for WizardBot AI behavior testing."""
    
    def __init__(self, server_name: str = "Test Simulation Server"):
        self.server_name = server_name
        self.channels: Dict[int, VirtualChannel] = {}
        self.roles: Dict[int, VirtualRole] = {
            1: VirtualRole(1, "everyone")
        }
        self.users: Dict[int, VirtualUser] = {
            999: VirtualUser(999, "AdminUser", roles=[1])
        }
        self.logs: List[str] = []
        self.shared_state: Dict[str, Any] = {}
        
        # Initialize basic structure
        self._add_channel("general", "text")
        self._add_channel("Voice", "voice")

    def _log(self, message: str):
        print(f"🎬 [VIRTUAL FIELD] {message}")
        self.logs.append(message)

    def _add_channel(self, name: str, char_type: str, category_id: int = None) -> int:
        cid = int(str(uuid.uuid4().int)[:12])
        self.channels[cid] = VirtualChannel(cid, name, char_type, category_id)
        self._log(f"Создан канал: {name} ({char_type}) [ID: {cid}]")
        return cid

    def _add_role(self, name: str, color: str = "#99aab5") -> int:
        rid = int(str(uuid.uuid4().int)[:12])
        self.roles[rid] = VirtualRole(rid, name, color)
        self._log(f"Создана роль: {name} [ID: {rid}]")
        return rid

    # --- Tool Execution Mocks ---
    
    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Simulates tool execution against the virtual state."""
        self._log(f"🛠️ ВЫЗОВ ИНСТРУМЕНТА: {name}({args})")
        
        if name == "create_category":
            cid = self._add_channel(args['name'], "category")
            return f"Категория создана. ID: {cid}"
            
        elif name == "create_text_channel":
            cat_id = None
            if args.get('category_name'):
                cat = next((c for c in self.channels.values() if c.type == "category" and (c.name == args['category_name'] or str(c.id) == str(args['category_name']))), None)
                if cat: cat_id = cat.id
            cid = self._add_channel(args['name'], "text", cat_id)
            return f"Текстовый канал создан. ID: {cid}"

        elif name == "create_voice_channel":
            cat_id = None
            if args.get('category_name'):
                cat = next((c for c in self.channels.values() if c.type == "category" and (c.name == args['category_name'] or str(c.id) == str(args['category_name']))), None)
                if cat: cat_id = cat.id
            cid = self._add_channel(args['name'], "voice", cat_id)
            return f"Голосовой канал создан. ID: {cid}"

        elif name == "list_channels":
            return "\n".join([f"- {c.name} (ID: {c.id}, Type: {c.type})" for c in self.channels.values()])

        elif name == "list_roles":
            return "\n".join([f"- {r.name} (ID: {r.id})" for r in self.roles.values() if r.name != "everyone"])

        elif name == "create_role":
            rid = self._add_role(args['name'], args.get('color_hex', "#99aab5"))
            return f"Роль создана. ID: {rid}"

        elif name == "query_users":
            q = args['query'].lower()
            found = [u for u in self.users.values() if q in u.name.lower()]
            if not found: return "Пользователи не найдены."
            return "\n".join([f"- {u.name} (ID: {u.id})" for u in found])

        elif name == "assign_role_to_user":
            u_id = int(args['user_name_or_id']) if args['user_name_or_id'].isdigit() else 0
            r_id = int(args['role_name_or_id']) if args['role_name_or_id'].isdigit() else 0
            if u_id in self.users and r_id in self.roles:
                self.users[u_id].roles.append(r_id)
                self._log(f"Роль {self.roles[r_id].name} назначена пользователю {self.users[u_id].name}")
                return "Успешно."
            return "Ошибка: Пользователь или роль не найдены."

        elif name == "ask_user_clarification":
            self._log(f"❓ ЗАПРОС УТОЧНЕНИЯ: {args['question']}")
            # Auto-answer for simulation? Let's return the first option or True
            return args.get('options', ["Yes"])[0]

        return f"Инструмент {name} выполнен (симуляция)."

    # --- Shared State (Mock for Reactive Pipelines) ---
    def set_shared_value(self, key: str, value: Any):
        self.shared_state[key] = value
        
    async def wait_for_shared_value(self, key: str, timeout: float = 5.0) -> Any:
        return self.shared_state.get(key)

    # --- Mock objects for AI Handler ---
    @property
    def guild(self):
        class MockGuild:
            def __init__(self, name, owner_id):
                self.name = name
                self.owner_id = owner_id
                self.member_count = 100
        return MockGuild(self.server_name, 999)

    @property
    def interaction(self):
        class MockInteraction:
            def __init__(self):
                self.user = type('obj', (object,), {'id': 999, 'name': 'AdminUser'})
                self.channel = type('obj', (object,), {'name': 'general'})
        return MockInteraction()

async def run_simulation(prompt: str):
    """Entry point to run a simulation of AI behavior."""
    from src.ai.handlers.timeweb import TimewebHandler
    from unittest.mock import AsyncMock, patch
    from src.core.managers.billing_manager import billing_manager

    # Mock DB calls
    billing_manager.save_message = AsyncMock()
    billing_manager.deduct_tokens = AsyncMock()

    field = VirtualField()
    handler = TimewebHandler()
    
    print(f"\n🚀 [SIMULATION START]")
    print(f"Запрос: {prompt}")
    print("-" * 40)
    
    async def status_callback(agent, text, node_id, parent_id, status="running"):
        color = "\033[94m" if status == "running" else "\033[92m" if status == "done" else "\033[91m"
        reset = "\033[0m"
        print(f"   {color}[{agent}]{reset} {text}")

    result = await handler.processed_prompt(
        prompt, 
        field, 
        status_callback=status_callback, 
        user_perms="administrator"
    )
    
    print("-" * 40)
    print(f"📊 [ИТОГОВЫЙ ОТВЕТ]:\n{result}")
    print(f"\n🌍 [СОСТОЯНИЕ МИРА ПОСЛЕ ТЕСТА]:")
    
    print(f"\n--- Роли ({len(field.roles)}) ---")
    for r in field.roles.values():
        print(f"  - {r.name} [ID: {r.id}]")
        
    print(f"\n--- Пользователи ({len(field.users)}) ---")
    for u in field.users.values():
        u_roles = [field.roles[rid].name for rid in u.roles if rid in field.roles]
        print(f"  - {u.name} [Роли: {', '.join(u_roles)}]")

    print(f"\n--- Каналы ({len(field.channels)}) ---")
    for c in field.channels.values():
        cat = f" (в категории {field.channels[c.category_id].name})" if c.category_id and c.category_id in field.channels else ""
        print(f"  - {c.name} [{c.type}]{cat}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Создай новую категорию 'Симуляция' и добавь туда текстовый канал 'тест-арена'"
    
    asyncio.run(run_simulation(query))
