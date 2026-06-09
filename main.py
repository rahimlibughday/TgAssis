import asyncio
from aiogram import Bot, Dispatcher
import config
from database import init_db, get_user_data
from handlers import router as registration_router
from services.scheduler import posting_loop


async def main():
    await init_db()
    print("[DB]Database initialized.")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(registration_router)
    print("[Bot]AI agent is active and ready to assist!")

    asyncio.create_task(posting_loop(bot))
    print("[Scheduler] Post scheduler started.")

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
