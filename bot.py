import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import os
from dotenv import load_dotenv

load_dotenv()

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import json

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
SHEET_NAME = os.getenv("SHEET_NAME")

# ================= GOOGLE SHEETS =================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ================= TELEGRAM =================
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_step = {}
user_data = {}

# ================= КНОПКИ =================

start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💍 Начать опрос", callback_data="start_survey")]
    ]
)

ATTEND_OPTIONS = ["Буду", "Не получится"]
TRANSFER_OPTIONS = ["Нужен трансфер", "Сам доберусь"]
STAY_OPTIONS = ["Уезжаю вечером", "До субботы", "До воскресенья"]

def make_kb(options):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in options],
        resize_keyboard=True
    )

kb_attend = make_kb(ATTEND_OPTIONS)
kb_transfer = make_kb(TRANSFER_OPTIONS)
kb_stay = make_kb(STAY_OPTIONS)

send_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📩 Отправить")]],
    resize_keyboard=True
)

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать! 💍\n\n"
        "Мы очень рады видеть вас на нашей свадьбе.\n"
        "Нажмите кнопку ниже, чтобы начать опрос 🤍",
        reply_markup=start_kb
    )

# ================= START SURVEY =================

@dp.callback_query(F.data == "start_survey")
async def start_survey(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_step[user_id] = "name"

    await callback.message.answer("Пожалуйста, укажите ваше имя и фамилию:")
    await callback.answer()

# ================= MAIN LOGIC =================

@dp.message()
async def handler(message: types.Message):
    user_id = message.from_user.id
    step = user_step.get(user_id)

    if not step:
        return

    # 1. NAME
    if step == "name":
        user_data[user_id] = {"name": message.text}
        user_step[user_id] = "attendance"

        await message.answer(
            "Сможете ли вы присутствовать?",
            reply_markup=kb_attend
        )

    # 2. ATTENDANCE
    elif step == "attendance":
        if message.text not in ATTEND_OPTIONS:
            await message.answer("Выберите вариант кнопкой 👇", reply_markup=kb_attend)
            return

        user_data[user_id]["attendance"] = message.text

        if message.text == "Не получится":
            save(user_data[user_id])
            await message.answer("Спасибо 🤍 Нам будет вас не хватать")
            user_step[user_id] = None
            return

        user_step[user_id] = "transfer"

        await message.answer(
            "Нужен ли вам трансфер?",
            reply_markup=kb_transfer
        )

    # 3. TRANSFER
    elif step == "transfer":
        if message.text not in TRANSFER_OPTIONS:
            await message.answer("Выберите вариант кнопкой 👇", reply_markup=kb_transfer)
            return

        user_data[user_id]["transfer"] = message.text
        user_step[user_id] = "stay"

        await message.answer(
            "Какие у вас планы после мероприятия?",
            reply_markup=kb_stay
        )

    # 4. STAY
    elif step == "stay":
        if message.text not in STAY_OPTIONS:
            await message.answer("Выберите вариант кнопкой 👇", reply_markup=kb_stay)
            return

        user_data[user_id]["stay"] = message.text
        user_step[user_id] = "confirm"
        await message.answer(
            "Почти готово 💍\n"
            "Нажмите кнопку, чтобы отправить ответы.",
            reply_markup=send_kb
        )

    # 5. CONFIRM SEND
    elif step == "confirm":
        if message.text != "📩 Отправить":
            await message.answer("Нажмите кнопку отправки 👇", reply_markup=send_kb)
            return

        save(user_data[user_id])

        await message.answer("Спасибо! 🤍\n""Ваши ответы сохранены. Ждём вас на свадьбе!")

        user_step[user_id] = None
        user_data.pop(user_id, None)

# ================= SAVE TO SHEETS =================

def save(data):
    sheet.append_row([
        data.get("name"),
        data.get("attendance"),
        data.get("transfer", "-"),
        data.get("stay", "-"),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ])

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())