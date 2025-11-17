from flask import Flask
import threading
import os
import main  # Импортируем ваш основной файл с ботом

app = Flask(__name__)

@app.route('/')
def home():
    return "Телеграм бот работает!"

def run_bot():
    # Запускаем главную функцию вашего бота
    main.main()

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)