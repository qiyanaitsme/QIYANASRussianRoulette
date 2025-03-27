import asyncio
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from tortoise import Tortoise
from config import BOT_TOKEN
from main_handlers import register_handlers

async def on_startup(_):
    try:
        await Tortoise.init(
            db_url="sqlite://db.sqlite3",
            modules={"models": ["models"]}
        )
        await Tortoise.generate_schemas()
    except Exception as e:
        print(f"Ошибка инициализации базы данных: {e}")
        raise

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    register_handlers(dp)
    await on_startup(dp)
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())