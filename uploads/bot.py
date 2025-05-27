# bot.py
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from src.database import init_db
from src.scheduler import start_scheduler
from src.reghandlers import register_handlers

logging.basicConfig(level=logging.INFO)
load_dotenv()
TOKEN = os.getenv("TOKEN")


async def main():
    # Инициализация БД и планировщика
    init_db()
    start_scheduler()

    # Бот и диспетчер
    storage = MemoryStorage()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)

    # Регистрируем все хэндлеры
    register_handlers(dp)

    # Запуск
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
