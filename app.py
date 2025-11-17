import asyncio
import logging
import os
import threading
from flask import Flask

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_async_code():
    """Запускает асинхронный код в отдельном потоке с собственным event loop"""
    try:
        # Создаем новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Импортируем и запускаем бота
        from main import main_async
        loop.run_until_complete(main_async())
    except Exception as e:
        logger.error(f"Ошибка в боте: {e}")

@app.route('/')
def home():
    return "✅ Бот работает! Проверь Telegram."

@app.route('/health')
def health():
    return "🟢 OK"

@app.route('/test')
def test():
    return "Веб-сервер работает нормально"

# Запускаем бота при старте приложения
if __name__ == '__main__':
    logger.info("Запускаем бота в отдельном потоке...")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_async_code, daemon=True)
    bot_thread.start()
    logger.info("Бот запущен в фоновом режиме")
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запускаем веб-сервер на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
