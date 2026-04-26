import os
import json
import asyncio
import uuid
import re
from typing import Any, Dict, List, Optional, Callable
from openai import AsyncOpenAI

from src.ai.specialists import SPECIALISTS
from src.tools.definitions import TOOLS

class TimewebHandler:
    """Handles interaction with Timeweb Cloud AI (OpenAI-compatible)."""
    
    def __init__(self):
        self.api_key = os.getenv("TIMEWEB_API_KEY")
        self.base_url = os.getenv("TIMEWEB_BASE_URL")
        self.model = "deepseek-v3"
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.show_usage = True
        self.active_agents = 0

    def _fix_types(self, obj: Any) -> Any:
        """Recursively fix type names for OpenAI compatibility."""
        if isinstance(obj, dict):
            return {k: (v.lower() if k == "type" and isinstance(v, str) else self._fix_types(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._fix_types(i) for i in obj]
        return obj

    def _tools_for_specialist(self, specialist_name: str, user_perms: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filters tools based on specialist requirements and user permissions."""
        spec = SPECIALISTS.get(specialist_name, SPECIALISTS["orchestrator"])
        tool_names = set(spec.get("tools", []))
        if not tool_names:
            return []

        is_admin = user_perms and "administrator" in user_perms
        openai_tools = []
        
        for tool in TOOLS:
            if tool["name"] not in tool_names:
                continue
            
            req_p = tool.get("required_perm")
            if is_admin or not req_p or (user_perms and req_p in user_perms):
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": self._fix_types(tool["parameters"])
                    }
                })
        return openai_tools

    def _usage_suffix(self, usage_context: Dict[str, int]) -> str:
        if not self.show_usage or not usage_context:
            return ""
        return f"\n\n`📊 {usage_context.get('total', 0)} tokens`"

    def _get_global_enforcement(self) -> str:
        return (
            "### ABSOLUTE EXECUTION MANDATE ###\n"
            "1. YOU ARE A ROBOTIC AUTOMATION SYSTEM. CONVERSATION IS FORBIDDEN.\n"
            "2. NEVER GIVE THE USER TUTORIALS. IF SOMETHING IS MISSING, CREATE IT.\n"
            "3. USE SEARCH TOOLS (query_users) IF INFORMATION IS LACKING.\n"
            "4. CALL TOOLS IMMEDIATELY. NO PREAMBLE.\n"
            "###################################"
        )

    async def _run_agent(
        self, 
        specialist_name: str, 
        prompt: str, 
        manager: Any, 
        status_callback: Optional[Callable] = None, 
        max_turns: int = 8, 
        usage_context: Optional[Dict[str, int]] = None, 
        parent_id: Optional[str] = None, 
        depth: int = 0, 
        forced_node_id: Optional[str] = None, 
        system_suffix: str = "", 
        user_perms: Optional[str] = None, 
        mode: str = "prompt", 
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        if depth > 3:
            return {"content": "Error: Recursion depth exceeded.", "reports": [], "stop_reason": "depth"}

        node_id = forced_node_id or str(uuid.uuid4())
        usage_context = usage_context if usage_context is not None else {"total": 0}
        
        specialist_name = specialist_name or "orchestrator"
        spec = SPECIALISTS.get(specialist_name, SPECIALISTS["orchestrator"])
        tools = self._tools_for_specialist(specialist_name, user_perms=user_perms)

        system_content = f"{system_suffix}\n{self._get_global_enforcement()}\nSPECIALIST ROLE: {spec['instruction']}"
        messages = [{"role": "system", "content": system_content}]
        if history: messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        reports = []

        async def update_status(text: str, status: str = "running"):
            if status_callback:
                try: await status_callback(specialist_name, text, node_id, parent_id, status=status)
                except: pass

        await update_status("🔄 Запускается")
        self.active_agents += 1

        try:
            last_msg = None
            for turn in range(max_turns):
                await update_status(f"💭 Ход {turn + 1}")

                try:
                    response = await self.client.chat.completions.create(
                        model=spec.get("model", self.model),
                        messages=messages,
                        tools=tools if tools else None,
                        tool_choice="auto" if tools else None,
                    )
                except Exception as e:
                    return {"content": f"AI Error: {e}", "reports": reports, "stop_reason": "error"}

                msg = response.choices[0].message
                last_msg = msg
                messages.append(msg)

                if response.usage:
                    usage_context["total"] += response.usage.total_tokens

                if not getattr(msg, "tool_calls", None):
                    # Protection against orchestrator hallucinating text instead of tools
                    if specialist_name == "orchestrator" and turn == 0 and not parent_id:
                        if len((msg.content or "").strip()) > 10:
                            # If it gave a long text instead of a tool call, force it to retry once
                            messages.append({"role": "user", "content": "ERROR: You are in STRICT OPERATIONAL MODE. You MUST call a tool (create_pipeline or delegate_to_sub_agent). Do not explain. Call the tool now."})
                            continue

                    await update_status("Завершено", status="done")
                    if not reports and specialist_name != "orchestrator":
                         reports.append(f"Инфо: {specialist_name} завершил работу без вызова инструментов.")
                    return {"content": (msg.content or "").strip(), "reports": reports, "stop_reason": None}

                # Tool execution
                tc_results = []
                for tc in msg.tool_calls:
                    name, args_raw = tc.function.name, tc.function.arguments or "{}"
                    try: args = json.loads(args_raw)
                    except: args = {}

                    res = await self._execute_tool_logic(
                        name, args, manager, status_callback, usage_context, 
                        node_id, depth, user_perms, mode, specialist_name
                    )
                    tc_results.append((tc.id, name, res))

                # Process results

                # Process results
                for t_id, t_name, res in tc_results:
                    res_content = res.get("content", "") if isinstance(res, dict) else str(res)
                    if isinstance(res, dict) and res.get("reports"):
                        reports.extend(res.get("reports"))
                    
                    if t_name not in ["list_channels", "list_roles", "list_server_info"]:
                        reports.append(f"[{t_name}]: {res_content}")

                    messages.append({"role": "tool", "tool_call_id": t_id, "name": t_name, "content": res_content})
                    
                    # Bypass logic
                    if isinstance(res, dict) and res.get("is_delegation") and res.get("success"):
                        await update_status("Успешно выполнено", status="done")
                        return {"content": res_content, "reports": reports, "stop_reason": None}

            return {"content": (getattr(last_msg, "content", None) or "").strip() or "Завершено.", "reports": reports, "stop_reason": None}
        finally:
            self.active_agents -= 1

    async def _execute_tool_logic(
        self, 
        name: str, 
        args: Dict[str, Any], 
        manager: Any, 
        status_callback: Optional[Callable], 
        usage_context: Dict[str, int], 
        node_id: str, 
        depth: int, 
        user_perms: Optional[str], 
        mode: str,
        specialist_name: str
    ) -> Any:
        """Unified logic to execute tools, including virtual tools like delegation."""
        
        async def update_status(text: str, status: str = "running"):
            if status_callback:
                try: await status_callback(specialist_name, text, node_id, None, status=status)
                except: pass

        if name == "delegate_to_sub_agent":
            sub_name = args.get("specialist_name")
            sub_tasks = args.get("tasks") or ([args.get("task")] if args.get("task") else [])
            
            if not sub_tasks:
                return "Error: No tasks provided."
            
            await update_status(f"🔀 Делегирую → {sub_name}")
            sub_runs = await asyncio.gather(*[
                self._run_agent(sub_name, st, manager, status_callback, usage_context=usage_context, parent_id=node_id, depth=depth+1, user_perms=user_perms, mode=mode)
                for st in sub_tasks
            ])
            
            s_reports, s_contents, success = [], [], True
            for r in sub_runs:
                if r.get("stop_reason") == "error": success = False
                if r.get("reports"): s_reports.extend(r.get("reports"))
                s_contents.append((r.get("content") or "").strip())
            
            return {"content": "\n\n".join(s_contents), "reports": s_reports, "success": success, "is_delegation": True}

        elif name == "create_pipeline":
            steps = args.get("steps", [])
            p_reports, context, success = [], {"last": None}, True
            print(f"🚀 [PIPELINE] Starting {len(steps)} steps for {specialist_name}")
            
            def resolve_variables(obj):
                """Recursively resolve {{var}} and $var in any object."""
                if isinstance(obj, str):
                    if obj.startswith("$"): return context.get(obj[1:], context["last"])
                    if "{{" in obj and "}}" in obj: return obj
                    return obj
                if isinstance(obj, list): return [resolve_variables(i) for i in obj]
                if isinstance(obj, dict): return {k: resolve_variables(v) for k, v in obj.items()}
                return obj

            for i, s in enumerate(steps):
                t_name, t_args = s.get("tool"), s.get("args", {})
                out_key = s.get("out")
                t_args = resolve_variables(t_args)
                
                async def resolve_reactive_deep(target):
                    nonlocal success
                    if not success: return target
                    if isinstance(target, str) and "{{" in target and "}}" in target:
                        matches = re.findall(r"\{\{(.*?)\}\}", target)
                        final_str = target
                        for m_val in matches:
                            step_id = f"{node_id}_step_{i}"
                            await update_status(f"🔗 Ожидание: {m_val}...")
                            if status_callback:
                                await status_callback(specialist_name, f"⏳ Ожидание сигнала: {m_val}", step_id, node_id, status="running")
                            resolved = await manager.wait_for_shared_value(m_val, timeout=60.0)
                            if resolved:
                                if status_callback:
                                    await status_callback(specialist_name, f"✅ Данные '{m_val}' получены", step_id, node_id, status="done")
                                final_str = final_str.replace("{{" + m_val + "}}", str(resolved))
                            else:
                                if status_callback:
                                    await status_callback(specialist_name, f"❌ Таймаут: {m_val}", step_id, node_id, status="error")
                                success = False; break
                        return final_str
                    if isinstance(target, list): return [await resolve_reactive_deep(i) for i in target]
                    if isinstance(target, dict): return {k: await resolve_reactive_deep(v) for k, v in target.items()}
                    return target

                t_args = await resolve_reactive_deep(t_args)
                if not success:
                    p_reports.append(f"Ошибка: Таймаут ожидания данных {{...}} на шаге {i+1}")
                    break

                step_id = f"{node_id}_step_{i}"
                if status_callback:
                    await status_callback(specialist_name, f"⚙️ Шаг {i+1}: {t_name}", step_id, node_id, status="running")
                
                try:
                    res = await self._execute_tool_logic(t_name, t_args, manager, status_callback, usage_context, step_id, depth+1, user_perms, mode, specialist_name)
                except Exception as e:
                    res = f"Ошибка: {e}"

                context["last"] = res
                res_str = res.get("content", "") if isinstance(res, dict) else str(res)
                
                # ID extraction
                extracted_id = None
                if isinstance(res_str, str):
                    m = re.search(r'ID: (\d+)', res_str)
                    if m: extracted_id = m.group(1)
                
                if extracted_id:
                    context["id"] = extracted_id
                    if out_key: manager.set_shared_value(out_key, extracted_id)
                
                p_reports.append(f"Шаг {i+1} ({t_name}): {res_str}")
                if status_callback:
                    st = "done" if "Ошибка" not in str(res_str) and "⛔" not in str(res_str) else "error"
                    await status_callback(specialist_name, f"✅ Шаг {i+1} завершен", step_id, node_id, status=st)

                if "Ошибка" in str(res_str) or "⛔" in str(res_str):
                    p_reports.append(f"⚠️ КРИТИЧЕСКИЙ СБОЙ на шаге {i+1}")
                    success = False; break
            
            return {"content": "Пайплайн завершен." if success else "Сбой пайплайна.", "reports": p_reports, "success": success}

        else:
            return await manager.execute_tool(name, args)

    async def processed_prompt(self, prompt: str, manager: Any, status_callback: Optional[Callable] = None, usage_context: Optional[Dict[str, int]] = None, user_perms: Optional[str] = None, mode: str = "prompt") -> str:
        from src.core.managers.billing_manager import billing_manager
        usage_context = usage_context if usage_context is not None else {"total": 0}

        p_lower = prompt.lower().strip()
        if p_lower in ["ку", "привет", "хай", "hello", "hi"]:
            return "👋 Привет! Я WizardBot. Чем могу помочь?"
        
        guild = manager.guild
        server_insight = f"\n[SERVER CONTEXT]: Server: '{guild.name}', Channel: '{manager.interaction.channel.name if (manager.interaction and manager.interaction.channel) else 'unknown'}', Members: {guild.member_count}"
        user_id = manager.interaction.user.id if manager.interaction else 0
        
        is_owner = guild.owner_id == user_id
        user_status = "\n[CALLER STATUS]: SERVER OWNER (GOD MODE)" if is_owner else "\n[CALLER STATUS]: REGULAR MEMBER"
        perms_info = f"{user_status}\n[CALLER DISCORD PERMISSIONS]: {user_perms or 'None'}{server_insight}"

        await billing_manager.save_message(user_id, "user", prompt)

        mode_turns = 10 if mode == "consult" else 6
        agent_name = "orchestrator" if len(prompt) >= 15 else "concierge"
        
        run = await self._run_agent(agent_name, prompt, manager, status_callback, max_turns=mode_turns, usage_context=usage_context, system_suffix=perms_info, user_perms=user_perms, mode=mode)
        
        content = (run.get("content") or "").strip()
        reports = run.get("reports") or []
        await billing_manager.save_message(user_id, "assistant", content)

        # Intelligence gluing
        if len(content) < 150 and reports:
            content += "\n\n**Результаты работы:**\n" + "\n".join(reports)

        # Editor phase
        if len(reports) > 1 and (len(content) > 600 or len(reports) > 2):
            try:
                editor_res = await self.client.chat.completions.create(
                    model=SPECIALISTS["chief_editor"]["model"],
                    messages=[
                        {"role": "system", "content": self._get_global_enforcement()},
                        {"role": "system", "content": SPECIALISTS["chief_editor"]["instruction"]},
                        {"role": "user", "content": f"Запрос:\n{prompt}\n\Отчеты:\n{chr(10).join(reports)}\n\nЧерновик:\n{content}"}
                    ],
                )
                if editor_res.usage: usage_context["total"] += editor_res.usage.total_tokens
                content = (editor_res.choices[0].message.content or "").strip()
            except: pass

        return content + self._usage_suffix(usage_context)

    async def process_with_plan(self, prompt: str, manager: Any, progress_callback: Callable, status_callback: Optional[Callable] = None, mode: str = "plan") -> str:
        usage = {"total": 0}
        run = await self._run_agent("orchestrator", prompt, manager, status_callback, max_turns=4, usage_context=usage, mode=mode)
        
        try:
            plan_res = await self.client.chat.completions.create(
                model=SPECIALISTS["orchestrator"]["model"],
                messages=[
                    {"role": "system", "content": "Составь краткий план (3–7 пунктов) для задачи. Без инструментов."},
                    {"role": "user", "content": prompt}
                ],
            )
            if plan_res.usage: usage["total"] += plan_res.usage.total_tokens
            plan_text = (plan_res.choices[0].message.content or "").strip()
        except: plan_text = "1. Выполнить задачу"

        if not await progress_callback(plan_text): return "CANCELLED"
        return await self.processed_prompt(f"{prompt}\n\nПлан:\n{plan_text}", manager, status_callback, usage_context=usage)

