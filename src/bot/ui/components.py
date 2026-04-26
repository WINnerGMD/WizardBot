import discord
import time
import re
from typing import List, Optional, Callable, Any

SPEC_LABELS = {
    "orchestrator": "🌀 ОРКЕСТРАТОР",
    "concierge": "🛎️ КОНСЬЕРЖ",
    "infra_architect": "🏗️ ИНФРА",
    "user_specialist": "👤 ЮЗЕРЫ",
    "mass_action_specialist": "⚡ МАСС-ОПС",
    "chat_specialist": "💬 ЧАТ",
    "chief_editor": "✍️ РЕДАКТОР"
}

ICONS = {
    "idle": "⬜",
    "running": "🔵",
    "done": "✅",
    "error": "🔴"
}

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

class TextInputModal(discord.ui.Modal, title="Ввод данных"):
    def __init__(self, question: str):
        super().__init__()
        self.answer = discord.ui.TextInput(
            label=question[:45], 
            style=discord.TextStyle.paragraph, 
            placeholder="Введите ваш ответ здесь..."
        )
        self.add_item(self.answer)
        self.result = None

    async def on_submit(self, interaction: discord.Interaction):
        self.result = self.answer.value
        await interaction.response.send_message("✅ Данные получены.", ephemeral=True)
        self.stop()

class ClarificationView(discord.ui.View):
    def __init__(self, owner_id: int, options: Optional[List[str]], input_type: str, question: str):
        super().__init__(timeout=120.0)
        self.owner_id = owner_id
        self.result = None
        
        mode = str(input_type).lower()
        
        # Ручной ввод
        manual_btn = discord.ui.Button(label="✍️ Свой вариант", style=discord.ButtonStyle.secondary)
        manual_btn.callback = self._manual_input_callback
        self.add_item(manual_btn)

        if mode == "boolean":
            self.add_item(self._create_button("Да", "True", discord.ButtonStyle.success))
            self.add_item(self._create_button("Нет", "False", discord.ButtonStyle.danger))

        elif "user" in mode:
            sel = discord.ui.UserSelect(placeholder="🔍 Выберите пользователя...", min_values=1, max_values=1)
            sel.callback = self._select_callback
            self.add_item(sel)
        elif "role" in mode:
            sel = discord.ui.RoleSelect(placeholder="🛡️ Выберите роль...", min_values=1, max_values=1)
            sel.callback = self._select_callback
            self.add_item(sel)
        
        # Обработка предложенных вариантов
        if not options and "?" in question:
            found = re.findall(r"['\"]([^'\"]+)['\"]", question)
            if not found and ":" in question:
                parts = question.split(":")[-1].split(",")
                found = [p.strip() for p in parts if len(p.strip()) < 30]
            options = found

        if mode == "buttons" and options:
            for c in options[:5]:
                self.add_item(self._create_button(str(c), str(c), discord.ButtonStyle.primary))
        elif ("select" in mode or "choice" in mode) and options:
            sel = discord.ui.Select(options=[discord.SelectOption(label=str(c)[:100]) for c in options[:25]])
            sel.callback = self._select_callback
            self.add_item(sel)

    def _create_button(self, label: str, value: str, style: discord.ButtonStyle):
        btn = discord.ui.Button(label=label[:80], style=style)
        async def callback(interaction: discord.Interaction):
            if interaction.user.id == self.owner_id:
                self.result = value
                self.stop()
                await interaction.response.edit_message(content=f"✅ Выбрано: **{label}**", view=None)
        btn.callback = callback
        return btn

    async def _manual_input_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id: return
        
        class InnerModal(discord.ui.Modal, title="Ручной ввод"):
            answer = discord.ui.TextInput(label="Введите ответ", placeholder="ID / Текст")
            def __init__(self, parent_view):
                super().__init__()
                self.parent = parent_view
            async def on_submit(self, it: discord.Interaction):
                self.parent.result = self.answer.value
                self.parent.stop()
                await it.response.send_message(f"✅ Введено: {self.answer.value}", ephemeral=True)
        
        await interaction.response.send_modal(InnerModal(self))

    async def _select_callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.owner_id:
            self.result = interaction.data['values'][0]
            label = self.result
            if interaction.data.get('resolved'):
                res = interaction.data['resolved']
                if 'users' in res: label = res['users'][self.result]['username']
                elif 'roles' in res: label = res['roles'][self.result]['name']
            self.stop()
            await interaction.response.edit_message(content=f"✅ Выбрано: **{label}**", view=None)

class PlanConfirmationView(discord.ui.View):
    def __init__(self, owner_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.confirmed = None

    @discord.ui.button(label="Утвердить", style=discord.ButtonStyle.success)
    async def ok(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.owner_id:
            self.confirmed = True
            self.stop()
            await interaction.response.defer()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.owner_id:
            self.confirmed = False
            self.stop()
            await interaction.response.defer()

def render_progress_board(board: dict) -> str:
    """Renders a beautiful hierarchical tree for task execution."""
    if not board:
        return "```ansi\n[ WIZARDBOT ] Ожидание задач...\n```"

    # 1. Сортируем по времени и строим дерево
    sorted_items = sorted(board.items(), key=lambda x: x[1]['tick'])
    nodes = {nid: {**data, "nid": nid, "children": []} for nid, data in sorted_items}
    roots = []
    
    for nid, node in nodes.items():
        pid = node.get('pid')
        if pid and pid in nodes:
            nodes[pid]['children'].append(node)
        else:
            roots.append(node)

    # 2. Оформление
    lines = [
        "```ansi", 
        "╔══════════════════════════════════════════════════════╗",
        "║             🔮  W I Z A R D  S T A T U S             ║",
        "╚══════════════════════════════════════════════════════╝"
    ]
    
    frame = int(time.time() * 5) % len(SPINNER)
    char = SPINNER[frame]

    def render_node(node, prefix="", is_last=True):
        status = node['status']
        spec_label = SPEC_LABELS.get(node['spec'], node['spec']) or "TASK"
        
        # Красивая иконка
        if status == "running":
            icon = f"\u001b[1;34m{char}\u001b[0m" # Анимированный спиннер
        elif status == "done":
            icon = "\u001b[1;32m●\u001b[0m" # Зеленая точка
        elif status == "error":
            icon = "\u001b[1;31m✖\u001b[0m" # Красный крест
        else:
            icon = "○"

        # Ветви дерева
        marker = "┗━ " if is_last else "┣━ "
        line_prefix = prefix + marker
        
        # Инфо
        text = str(node.get('text', '...'))
        # Цветовое кодирование текста
        if "📡" in text or "Сигнал" in text:
            text = f"\u001b[1;36m{text}\u001b[0m" # Циановый для сигналов
        elif "⏳" in text or "Ожидание" in text or "🔗" in text:
            text = f"\u001b[1;33m{text}\u001b[0m" # Желтый для ожидания
        elif "Шаг" in text or "⚙️" in text:
            text = f"\u001b[1;37m{text}\u001b[0m" # Белый для шагов
        
        # Подсветка имени специалиста (только для корневых или если это другой специалист)
        if not node.get('pid'):
            label = f"\u001b[1;35m{spec_label}\u001b[0m" # Фиолетовый для главных
        else:
            # Для вложенных шагов можно использовать сокращенную метку или серый цвет
            label = f"\u001b[1;30m{spec_label[:10]}\u001b[0m"

        elapsed = int(time.time() - node['tick'])
        time_str = f"\u001b[1;30m{elapsed}s\u001b[0m"
        
        # Форматирование строки
        lines.append(f"{line_prefix}{icon} {label:<15} {text:<35} {time_str:>4}")
        
        # Рекурсия для детей
        new_prefix = prefix + ("    " if is_last else "┃   ")
        for i, child in enumerate(node['children']):
            render_node(child, new_prefix, i == len(node['children']) - 1)

    for i, root in enumerate(roots):
        render_node(root, "", i == len(roots) - 1)
    
    lines.append("```")
    return "\n".join(lines)
