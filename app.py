import asyncio
import logging
import os
from flask import Flask
import threading
import requests
import time

app = Flask(__name__)

# Импортируем бота отдельно чтобы избежать циклических импортов
def run_bot():
    """Запускает бота в отдельном процессе"""
    import main
    asyncio.run(main.main_async())

@app.route('/')
def home():
    return "✅ Бот работает! Проверь Telegram."

@app.route('/health')
def health():
    return "🟢 OK"

def start_bot():
    """Запускает бота в отдельном потоке"""
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logging.info("Бот запущен в отдельном потоке")

# Запускаем бота при старте приложения
if __name__ == '__main__':
    start_bot()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
