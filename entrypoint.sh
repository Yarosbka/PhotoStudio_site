#!/bin/sh

# Ждем, пока база данных (сервис db) станет доступна на порту 3306
echo "Waiting for mysql..."
while ! nc -z db 3306; do
  sleep 0.1
done
echo "MySQL started"

# Применяем миграции базы данных
echo "Applying DB migrations..."
flask db upgrade

# (Опционально) Можно автоматически заполнять базу при первом старте
# python seed.py 

# Запускаем Gunicorn
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 run:app