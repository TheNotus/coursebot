import asyncio
import logging
import threading
import uvicorn

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import BOT_TOKEN
from .data_manager.database import Database
from .bot.handlers import router


# Настройка логирования
logging.basicConfig(level=logging.INFO)


def run_web_server():
    """Функция для запуска веб-сервера в отдельном потоке"""
    # Импортируем приложение FastAPI из модуля
    from .web_app.main import app
    
    # Запускаем uvicorn сервер
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


async def main():
    # Запуск веб-сервера в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Инициализация базы данных
    db = Database()
    await db.init_db()
    
    # Добавление базы данных к объекту бота для передачи в обработчики
    bot.db = db
    
    # Регистрация роутера
    dp.include_router(router)
    
    # Удаление вебхука перед запуском поллинга
    await bot.delete_webhook()
    
    # Запуск бота в режиме long polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())