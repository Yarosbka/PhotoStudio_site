# Используем легкий образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Запрещаем Python писать pyc файлы и буферизировать вывод (чтобы логи видеть сразу)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости (netcat нужен для проверки доступности БД)
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python + Gunicorn
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Копируем весь код проекта
COPY . .

# Делаем скрипт запуска исполняемым
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Открываем порт 5000
EXPOSE 5000

# Запускаем скрипт
ENTRYPOINT ["./entrypoint.sh"]