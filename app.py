import os
import logging
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite

# --- تنظیمات لگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- تنظیمات اصلی ---
BOT_TOKEN = os.getenv("BOT_TOKEN")  # باید در Render تنظیم شود
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set in environment variables!")
    raise ValueError("BOT_TOKEN environment variable not set")

# --- FastAPI برای Health Check ---
fastapi_app = FastAPI()

@fastapi_app.get("/healthz")
async def health_check():
    """Endpoint برای UptimeRobot/Cron-job"""
    return {"status": "ok", "bot": "running"}

# --- Aiogram (بات تلگرام) ---
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# --- دیتابیس SQLite ---
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                start_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# --- هندلرهای بات ---
@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "N/A"

    async with aiosqlite.connect("bot.db") as db:
        # چک کردن کاربر
        cur = await db.execute("SELECT start_count FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()

        if row:
            # کاربر قدیمی
            new_count = row[0] + 1
            await db.execute(
                "UPDATE users SET start_count = ?, username = ? WHERE user_id = ?",
                (new_count, username, user_id)
            )
            await message.answer(
                f"👋 <b>خوش آمدی دوباره!</b>\n\n"
                f"شما قبلا {row[0]} بار /start زدید."
            )
        else:
            # کاربر جدید
            await db.execute(
                "INSERT INTO users (user_id, username, start_count) VALUES (?, ?, 1)",
                (user_id, username)
            )
            await message.answer(
                f"🎉 <b>خوش آمدی!</b>\n\n"
                f"این اولین بار است که از بات استفاده می‌کنی."
            )
        await db.commit()

# --- استارت FastAPI + Aiogram ---
@fastapi_app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("Starting bot polling...")
    asyncio.create_task(dp.start_polling(bot))

# --- برای اجرای مستقیم (مورد نیاز نیست، فقط برای تست) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
