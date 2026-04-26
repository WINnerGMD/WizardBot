import asyncio
import re
from google import genai
from google.genai import types
from src.core.key_manager import key_manager
from src.ai.specialists import SPECIALISTS

class GeminiHandler:
    def __init__(self):
        self.last_usage = {"input": 0, "output": 0, "total": 0}
        self.worker_reports = {}
        self.show_usage = True

    def _update_tokens(self, response):
        if response and response.usage_metadata:
            self.last_usage["input"] += response.usage_metadata.prompt_token_count
            self.last_usage["output"] += response.usage_metadata.candidates_token_count
            self.last_usage["total"] += response.usage_metadata.total_token_count

    def reset_usage(self):
        import os
        self.last_usage = {"input": 0, "output": 0, "total": 0}
        self.frozen_count_in_request = 0
        self.worker_reports = {}
        self.show_usage = os.getenv("WIZARDBOT_SHOW_USAGE", "").strip() in ("1", "true", "yes", "on")

    def _usage_suffix(self):
        if not self.show_usage:
            return ""
        return f"\n\n`📊 {self.last_usage['total']} tokens`"

    async def _create_instance(self, specialist_name="architect"):
        from src.tools.definitions import TOOLS as ALL_TOOLS
        api_key = await key_manager.get_valid_key()
        client = genai.Client(api_key=api_key)
        
        # Инструкции специалистов
        spec = SPECIALISTS.get(specialist_name, SPECIALISTS["architect"])
        
        # Сопоставляем имена инструментов с их определениями
        tool_names = spec.get("tools", [])
        active_tools = [t for t in ALL_TOOLS if t["name"] in tool_names]
        
        # Формируем список инструментов для Google SDK
        gemini_tools = []
        if active_tools:
            declarations = [
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t.get("parameters")
                ) for t in active_tools
            ]
            gemini_tools = [types.Tool(function_declarations=declarations)]

        config = types.GenerateContentConfig(
            system_instruction=spec["instruction"],
            tools=gemini_tools,
            temperature=0.7
        )
        return client, config, spec["model"], api_key

    async def _run_sub_agent(self, specialist_name, task, manager, status_callback=None):
        if status_callback: await status_callback("Wizardbot выполняет задачу…")
        client, config, model_name, api_key = await self._create_instance(specialist_name)
        
        prompt = f"Твоя задача: {task}\nВыполни её и дай краткий отчет."
        response = await self._safe_generate(client, model_name, [types.Content(role="user", parts=[types.Part(text=prompt)])], config, api_key)
        
        res_text = response.text if response else "Ошибка выполнения под-агента."
        self.worker_reports[specialist_name] = f"### Отчет {specialist_name}:\n{res_text}"
        return res_text

    async def _safe_generate(self, client, model, contents, config, api_key, status_callback=None):
        total_parts = 0
        for c in contents:
            for p in c.parts:
                if p.text: total_parts += len(p.text)
        print(f"📡 Запрос ({api_key[:6] if api_key else 'None'}): {model} | Контекст: ~{total_parts} симв.")

        for attempt in range(30): # Пробуем до 30 ключей за раз
            if self.frozen_count_in_request > 25:
                print("🚨 [CIRCUIT BREAKER] Слишком много заморозок! Аварийная остановка.")
                raise RuntimeError("CIRCUIT_BREAKER_TRIGGERED")
            
            if not api_key:
                api_key = await key_manager.get_valid_key()
                if not api_key:
                    msg = "⏳ Все ключи заняты, сплю 3с..."
                    print(msg)
                    if status_callback: await status_callback("Wizardbot занят ключами, пробую снова…")
                    await asyncio.sleep(3)
                    continue
                client = genai.Client(api_key=api_key)

            try:
                response = await asyncio.to_thread(client.models.generate_content, model=model, contents=contents, config=config)
                self._update_tokens(response)
                return response
            except Exception as e:
                err = str(e).lower()
                print(f"📡 [FULL ERROR] {err}")
                
                if any(x in err for x in ["safety", "invalid", "400", "blocked", "candidate"]):
                    print(f"🛑 [STOP] Ошибка контента.")
                    raise e

                if "429" in err or "resource_exhausted" in err:
                    limit_match = re.search(r'limit: (\d+)', err)
                    limit_val = int(limit_match.group(1)) if limit_match else 15
                    
                    # КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Если лимит 0 - это труп на сегодня.
                    if limit_val == 0:
                        print(f"💀 Проект {api_key[:6]} имеет квоту 0. Замораживаю на сутки.")
                        await key_manager.mark_exhausted(api_key, status='DAILY_LIMIT', cooldown_seconds=86400)
                        self.frozen_count_in_request += 1
                    else:
                        retry_match = re.search(r'retry in ([\d\.]+)s', err)
                        if retry_match:
                            wait = int(float(retry_match.group(1))) + 2
                            print(f"⏳ Ключ {api_key[:6]} занят (retry in {wait}s). Следующий...")
                            await key_manager.mark_exhausted(api_key, status='RATE_LIMITED', cooldown_seconds=wait) 
                        elif limit_val in [1500, 2000]:
                            print(f"🚫 DAILY_LIMIT ({api_key[:6]}).")
                            await key_manager.mark_exhausted(api_key, status='DAILY_LIMIT', cooldown_seconds=86400)
                            self.frozen_count_in_request += 1
                        else:
                            print(f"⏳ RPM/TPM ({api_key[:6]}). Следующий...")
                            await key_manager.mark_exhausted(api_key, status='RATE_LIMITED', cooldown_seconds=15) 

                    api_key = await key_manager.get_valid_key()
                    client = genai.Client(api_key=api_key)
                    continue
                
                if any(x in err for x in ["403", "suspended", "unauthorized"]):
                    print(f"💀 Ключ {api_key[:6]} забанен Google. Выкидываю из пула.")
                    await key_manager.mark_exhausted(api_key, status='BANNED')
                    self.frozen_count_in_request += 1
                    api_key = await key_manager.get_valid_key()
                    client = genai.Client(api_key=api_key)
                    continue

                # Любая другая неизвестная ошибка — лучше упасть, чем сжечь все ключи
                print(f"❓ Неизвестная ошибка ({api_key[:6]}): {err}")
                raise e
        return None

    async def processed_prompt(self, prompt, manager, status_callback=None):
        self.reset_usage()
        client, config, model_name, api_key = await self._create_instance()
        
        if status_callback: await status_callback("Wizardbot думает…")
        current_contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        all_reports = []
        response = None
        
        workflow_status = {} # {worker_id: {"name": "...", "task": "...", "status": "⏳"}}
        
        async def update_ui(main_msg):
            if status_callback: await status_callback(main_msg)

        for turn in range(5):
            # Триммер истории
            if len(current_contents) > 6:
                current_contents = [current_contents[0]] + current_contents[-5:]

            # На первом ходу не пугаем пользователя техническими деталями
            if turn > 0:
                await update_ui("Wizardbot уточняет детали и собирает изменения…")
            
            response = await self._safe_generate(client, model_name, current_contents, config, api_key, None)
            if not response: break
            
            res_content = response.candidates[0].content
            current_contents.append(res_content)
            
            tool_calls = [p.function_call for p in res_content.parts if p.function_call]
            
            # ШОРТКАТ: Если это первый ход и нет вызова функций - это ПРОСТО ОТВЕТ
            if turn == 0 and not tool_calls:
                text_out = res_content.parts[0].text if res_content.parts else "Запрос принят."
                if status_callback: await status_callback("Готово.")
                return text_out + self._usage_suffix()

            if not tool_calls: break
            
            tool_responses, should_stop, report = await self._handle_calls(tool_calls, manager, status_callback, workflow_status, update_ui)
            if report: all_reports.append(report)
            current_contents.append(types.Content(role="user", parts=tool_responses))
            if should_stop: break
            
        if response is None or not response.candidates:
            return "❌ Ошибка: Превышено количество попыток. Попробуй через минуту."

        # Финальный этап: Формирование отчета через 'Output Engine'
        if status_callback: await status_callback("Формирую ответ…")
        
        if all_reports:
            summary = "\n".join([f"🔹 {r}" for r in all_reports])
        else:
            summary = response.candidates[0].content.parts[0].text or "Запрос выполнен."

        print(f"📡 [DEBUG] Summary for messenger: {summary[:100]}...")
        final_out = await self._run_sub_agent("chief_editor", f"Исходный запрос: {prompt}\n\nСДЕЛАНО:\n{summary}", manager)
        
        return final_out + self._usage_suffix()

    async def _handle_calls(self, tool_calls, manager, status_callback, workflow_status=None, update_ui=None):
        parts = []
        should_stop = False
        report_accum = []
        async def run_call(call):
            name = call.name
            args = call.args
            
            # Если это вызов субагента, обновляем дерево статусов
            if name == "delegate_to_sub_agent" and workflow_status is not None:
                spec = args.get("specialist_name", "unknown")
                task = args.get("task") or (args.get("tasks")[0] if args.get("tasks") else "Parallel Tasks")
                worker_id = f"{spec}_{len(workflow_status)}"
                workflow_status[worker_id] = {"name": spec.upper(), "task": task, "status": "RUN"}
                if update_ui: await update_ui(f"Запуск специалиста {spec}...")

            if name == "delegate_to_sub_agent":
                tasks = args.get('tasks', []) or [args.get('task', '')]
                sub_res = await asyncio.gather(*[
                    self._run_sub_agent(args['specialist_name'], t, manager, status_callback) for t in tasks if t
                ])
                
                # Помечаем воркера как выполненного
                if workflow_status is not None:
                    for k in workflow_status:
                        if workflow_status[k]["status"] == "RUN": 
                            workflow_status[k]["status"] = "DONE"
                    if update_ui: await update_ui(f"Специалист {args['specialist_name']} завершил работу")
                
                return name, " | ".join(sub_res)
            elif name == "submit_execution_plan":
                nonlocal should_stop
                res = [await manager.execute_tool(a['action_name'], a['args']) for a in args.get('actions', [])]
                should_stop = True
                return name, "\n".join(res)
            else:
                return name, await manager.execute_tool(name, args)

        results = await asyncio.gather(*[run_call(c) for c in tool_calls])
        for name, res in results:
            parts.append(types.Part(function_response=types.FunctionResponse(name=name, response={'result': res})))
            report_accum.append(res)
        return parts, should_stop, "\n".join(report_accum)

    async def process_with_plan(self, prompt, manager, progress_callback, status_callback=None):
        self.reset_usage()
        client, config, model_name, api_key = await self._create_instance()
        
        # Составляем план
        res = await self._safe_generate(client, model_name, [types.Content(role="user", parts=[types.Part(text=f"План для: {prompt}")])], config, api_key)
        plan = res.text if res else "Ошибка составления плана."
        
        if not await progress_callback(plan):
            return "CANCELLED"
            
        return await self.processed_prompt(f"Выполни план: {plan}", manager, status_callback)
