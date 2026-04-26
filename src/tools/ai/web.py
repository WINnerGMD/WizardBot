import aiohttp
import asyncio
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from typing import Any, Dict
from src.tools.base import BaseTool, ToolContext, registry

class SearchWebTool(BaseTool):
    name = "search_web"
    
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        query = args.get("query")
        if not query:
            return "⛔ ОШИБКА: Не указан поисковый запрос (query)."
        
        limit = min(int(args.get("limit", 5)), 10)
        
        def do_search():
            results = []
            with DDGS() as ddgs:
                try:
                    for r in ddgs.text(query, max_results=limit):
                        results.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}")
                except Exception as e:
                    return f"Ошибка поиска: {e}"
            return "\n\n".join(results) if results else "Ничего не найдено."

        return await asyncio.to_thread(do_search)

class ReadWebpageTool(BaseTool):
    name = "read_webpage"
    
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        url = args.get("url")
        if not url:
            return "⛔ ОШИБКА: Не указан URL."
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return f"Ошибка HTTP {response.status} при загрузке страницы."
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Удаляем скрипты и стили
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.extract()
                        
                    text = soup.get_text(separator='\n')
                    
                    # Очистка пустых строк
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    # Ограничиваем длину текста
                    max_len = 15000
                    if len(text) > max_len:
                        text = text[:max_len] + "\n[Текст обрезан из-за превышения лимита]"
                        
                    return f"Содержимое страницы {url}:\n\n{text}"
                    
        except Exception as e:
            return f"Ошибка чтения страницы: {str(e)}"

# Registering tools
registry.register(SearchWebTool())
registry.register(ReadWebpageTool())
