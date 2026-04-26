FROM python:3.11-slim

WORKDIR /app

# Не создавать .pyc файлы и не буферизировать вывод, чтобы логи сразу шли в консоль
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Копируем остальной код
COPY . .

# Запускаем бота
CMD ["python", "main.py"]
