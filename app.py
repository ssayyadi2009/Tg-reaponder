import os
import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite

# --- تنظیمات ---
BOT_TOKEN = os.environ["BOT_TOKEN"]  # باید در Render تنظیم شود
DB_PATH = "bot.db"

# --- متون بات ---
FIRST_START_TEXT = "سلام! نخستین بار است که /start می‌زنید."
REPEAT_START_TEXT = "خوش آمدید دوباره! از منو گزینه‌ای رو انتخاب کنید."

# --- FastAPI (برای Health Check) ---
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# --- دیتابیس SQLite ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, start_count INTEGER DEFAULT 0)")
        await db.commit()

async def get_start_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT start_count FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0

async def increment_start_count(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.execute("UPDATE users SET start_count = start_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

# --- Aiogram (بات تلگرام) ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def on_start(message: Message):
    user_id = message.from_user.id
    count = await get_start_count(user_id)
    if count == 0:
        await message.answer(FIRST_START_TEXT)
    else:
        await message.answer(REPEAT_START_TEXT)
    await increment_start_count(user_id)

# --- استارت FastAPI + Aiogram ---
@app.on_event("startup")
async def on_startup():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
