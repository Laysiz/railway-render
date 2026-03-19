# backend/wsgi.py
import os
import sys

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем приложение (измените 'app' на фактическое имя вашей Flask-переменной)
try:
    # Если ваша Flask-переменная называется 'app'
    from app import app as application
except ImportError:
    try:
        # Если ваша Flask-переменная называется 'application'
        from app import application
    except ImportError:
        # Если ваша Flask-переменная называется иначе, укажите правильное имя
        from app import your_flask_app_var as application

# Это стандартное имя для WSGI
app = application

if __name__ == "__main__":
    app.run()