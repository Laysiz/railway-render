# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY backend/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Переходим в папку backend для запуска
WORKDIR /app/backend

# Указываем порт
ENV PORT=10000

# Запускаем приложение
CMD gunicorn --bind 0.0.0.0:$PORT wsgi:app