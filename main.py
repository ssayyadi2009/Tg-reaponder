import os
import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN env var in Render dashboard.")

DB_PATH = "bot.db"

FIRST_START_TEXT = (
    "سلام! خوش اومدی 👋\n"
    "این پیام فقط اولین بار که /start بزنی ارسال می‌شود."
)

REPEAT_START_TEXTS = [
    "سلام مجدد! از منو گزینه‌ای رو انتخاب کن.",
    "باز هم خوش اومدی! /help رو بزن برای راهنما.",
    "در خدمتم—چه کاری می‌تونم انجام بدم؟",
]

SEND_REPEAT_RANDOM = False

# ---------- FastAPI برای سلامت سرویس ----------
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# ---------- دیتابیس ----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                start_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.commit()

async def get_and_increment_start_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT start_count FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT INTO users (user_id, start_count) VALUES (?, ?)", (user_id, 1))
            await db.commit()
            return 0
        prev = int(row[0])
        await db.execute("UPDATE users SET start_count = start_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return prev

def pick_repeat_text(prev_count: int) -> str:
    if not REPEAT_START_TEXTS:
        return "سلام! (فعلاً متنی برای دفعات بعد تعریف نشده)"
    if SEND_REPEAT_RANDOM:
        import random
        return random.choice(REPEAT_START_TEXTS)
    idx = (prev_count - 1) % len(REPEAT_START_TEXTS)
    return REPEAT_START_TEXTS[idx]

# ---------- Aiogram ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def on_start(message: Message):
    prev = await get_and_increment_start_count(message.from_user.id)
    if prev == 0:
        await message.answer(FIRST_START_TEXT)
    else:
        await message.answer(pick_repeat_text(prev))

@dp.message(Command("help"))
async def on_help(message: Message):
    await message.answer("راهنما:\n/start شروع\n/help راهنما")

# رویداد استارتاپ FastAPI: اجرای polling به صورت task پس‌زمینه
@app.on_event("startup")
async def on_startup():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
