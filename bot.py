import asyncio
import logging
import random
import string
import time
import re
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram import F

from config import TOKEN, ADMIN_ID, GAME_EMOJI
from database import *
from games import (
    start_mines, open_cell, cashout, get_active_game,
    play_slots, play_dice, play_basketball,
    start_roulette, add_bet, add_mass_bet, show_bets,
    cancel_bets, spin_roulette, active_roulettes,
    create_result_keyboard, double_bet, repeat_bet, last_bets,
    start_pyramid, pyramid_door, pyramid_cashout, pyramid_end, active_pyramids,
    start_rocket, rocket_cashout, rocket_stop, active_rockets
)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

active_games = {}

def is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"

# ================= КЛАВИАТУРЫ =================

def get_main_reply_keyboard_with_webapp():
    """Главное меню с синей кнопкой Web App"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 ИГРЫ"), KeyboardButton(text="👤 ПРОФИЛЬ")],
            [KeyboardButton(text="🎁 БОНУС"), KeyboardButton(text="🏆 ТОП")],
            [KeyboardButton(text="💸 ПЕРЕВОД"), KeyboardButton(text="🎫 ПРОМОКОД")],
            [KeyboardButton(text="🔵 ПРИЛОЖЕНИЕ", web_app=WebAppInfo(url="https://tackiness-jacket-guacamole.ngrok-free.dev"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_games_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💣 МИНЫ"), KeyboardButton(text="🎰 СЛОТЫ")],
            [KeyboardButton(text="🎲 КОСТИ"), KeyboardButton(text="🏀 БАСКЕТБОЛ")],
            [KeyboardButton(text="🎡 РУЛЕТКА"), KeyboardButton(text="🏛️ ПИРАМИДА")],
            [KeyboardButton(text="🚀 РАКЕТА"), KeyboardButton(text="🔙 НАЗАД")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_roulette_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 СТАВКИ"), KeyboardButton(text="💰 УДВОИТЬ")],
            [KeyboardButton(text="🔄 ПОВТОРИТЬ"), KeyboardButton(text="❌ ОТМЕНИТЬ")],
            [KeyboardButton(text="🎡 КРУТИТЬ"), KeyboardButton(text="🔙 ГЛАВНОЕ МЕНЮ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

# ================= СТАРТ =================
@dp.message(CommandStart())
async def start_cmd(message: Message):
    uid = message.from_user.id
    create_user(uid, message.from_user.first_name, message.from_user.username)
    
    # Используем новую клавиатуру с Web App кнопкой
    keyboard = get_main_reply_keyboard_with_webapp() if is_private_chat(message) else None
    
    await message.answer(
        f"✨ <b>Drunk</b> ✨\n\n"
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"💰 Твой баланс: <b>{get_balance(uid)} DRUNK</b>\n\n"
        f"👇 Выбирай действие в меню:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

# ================= ГЛАВНОЕ МЕНЮ =================

@dp.message(lambda m: m.text and m.text == "🎮 ИГРЫ" and is_private_chat(m))
async def games_menu(message: Message):
    keyboard = get_games_reply_keyboard()
    await message.answer("🎮 <b>ВЫБЕРИ ИГРУ</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text == "👤 ПРОФИЛЬ" and is_private_chat(m))
async def profile_btn(message: Message):
    uid = message.from_user.id
    cursor.execute("SELECT balance, wins, loses, total_bet, total_win FROM users WHERE user_id=?", (uid,))
    u = cursor.fetchone()
    await message.answer(
        f"👤 <b>ТВОЙ ПРОФИЛЬ</b>\n\n"
        f"💰 Баланс: <b>{u[0]}</b> DRUNK\n"
        f"🏆 Победы: {u[1]}\n"
        f"💀 Поражения: {u[2]}\n"
        f"📊 Всего игр: {u[1] + u[2]}\n"
        f"💸 Поставлено: {u[3]}\n"
        f"🎉 Выиграно: {u[4]}",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🎁 БОНУС" and is_private_chat(m))
async def bonus_btn(message: Message):
    uid = message.from_user.id
    if can_take_bonus(uid):
        take_bonus(uid)
        await message.answer(f"🎁 <b>+2500 DRUNK</b>\n\n💰 Новый баланс: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
    else:
        await message.answer("⏰ <b>Бонус ещё не доступен!</b>\nПопробуй через 24 часа", parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text == "🏆 ТОП" and is_private_chat(m))
async def top_btn(message: Message):
    top = get_top_users()
    if not top:
        await message.answer("❌ Нет пользователей!")
        return
    text = "🏆 <b>ТОП ИГРОКОВ</b> 🏆\n\n"
    for i, (uid, balance) in enumerate(top, 1):
        text += f"{i}. {get_user_name(uid)} — {balance} DRUNK\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text == "💸 ПЕРЕВОД" and is_private_chat(m))
async def transfer_menu(message: Message):
    await message.answer(
        "💸 <b>ПЕРЕВОД ДЕНЕГ</b>\n\n"
        "📝 <b>Как перевести:</b>\n"
        "├ <code>п 100 @username</code> - перевести по юзернейму\n"
        "└ Ответь на сообщение и напиши <code>п 100</code>\n\n"
        "💰 Минимальная сумма: 10 DRUNK",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🎫 ПРОМОКОД" and is_private_chat(m))
async def promo_menu(message: Message):
    await message.answer(
        "🎫 <b>ПРОМОКОДЫ</b>\n\n"
        "📝 <b>Как активировать:</b>\n"
        "└ Напиши <code>ПРОМОКОД НАЗВАНИЕ</code>\n\n"
        "Пример: <code>ПРОМОКОД WELCOME</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🔙 НАЗАД" and is_private_chat(m))
async def back_to_main(message: Message):
    keyboard = get_main_reply_keyboard()
    await message.answer("🔙 <b>ГЛАВНОЕ МЕНЮ</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text == "🔙 ГЛАВНОЕ МЕНЮ" and is_private_chat(m))
async def back_to_main_from_roulette(message: Message):
    keyboard = get_main_reply_keyboard()
    await message.answer("🔙 <b>ГЛАВНОЕ МЕНЮ</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML)

# ================= КНОПКИ ИГР =================

@dp.message(lambda m: m.text and m.text == "💣 МИНЫ" and is_private_chat(m))
async def mines_btn(message: Message):
    await message.answer(
        "💣 <b>МИНЫ</b>\n\n"
        "📝 <b>Как играть:</b>\n"
        "├ <code>мины 100 5</code> - начать игру\n"
        "├ <code>open 7</code> - открыть клетку\n"
        "└ <code>cashout</code> - забрать выигрыш\n\n"
        "💰 Минимальная ставка: 10 DRUNK\n"
        "💣 Мины: 1-24",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🎰 СЛОТЫ" and is_private_chat(m))
async def slots_btn(message: Message):
    await message.answer(
        "🎰 <b>СЛОТЫ</b>\n\n"
        "📝 <b>Как играть:</b>\n"
        "├ <code>слоты 100</code> - крутить слоты\n\n"
        "💰 Минимальная ставка: 10 DRUNK\n"
        "🎰 Множители: x1.5 - x50",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🎲 КОСТИ" and is_private_chat(m))
async def dice_btn(message: Message):
    await message.answer(
        "🎲 <b>КОСТИ</b>\n\n"
        "📝 <b>Как играть:</b>\n"
        "├ <code>кости 100</code> - бросить кости\n\n"
        "💰 Минимальная ставка: 10 DRUNK\n"
        "🎲 Множитель: x2 при победе",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🏀 БАСКЕТБОЛ" and is_private_chat(m))
async def basketball_btn(message: Message):
    await message.answer(
        "🏀 <b>БАСКЕТБОЛ</b>\n\n"
        "📝 <b>Как играть:</b>\n"
        "├ <code>баскет 100</code> - средний (x2.5)\n"
        "├ <code>баскет легкий 100</code> - легкий (x1.5)\n"
        "└ <code>баскет сложный 100</code> - сложный (x3.5)\n\n"
        "💰 Минимальная ставка: 10 DRUNK",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🎡 РУЛЕТКА" and is_private_chat(m))
async def roulette_btn(message: Message):
    await start_roulette(message)

@dp.message(lambda m: m.text and m.text == "🏛️ ПИРАМИДА" and is_private_chat(m))
async def pyramid_btn(message: Message):
    await message.answer(
        "🏛️ <b>ПИРАМИДА УДАЧИ</b> 🏛️\n\n"
        "📝 <b>Как играть:</b>\n"
        "├ <code>пирамида 100</code> - начать игру со ставкой 100\n\n"
        "🎮 <b>Правила:</b>\n"
        "├ Выбирай дверь на каждом уровне\n"
        "├ За одной из дверей - проход дальше\n"
        "├ За остальными - проигрыш\n"
        "├ С каждым уровнем множитель растёт!\n\n"
        "💰 Минимальная ставка: 10 DRUNK",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text == "🚀 РАКЕТА" and is_private_chat(m))
async def rocket_webapp_btn(message: Message):
    uid = message.from_user.id
    webapp_url = f"https://drunk-webapp.onrender.com/rocket?user_id={uid}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ЗАПУСТИТЬ РАКЕТУ", web_app=WebAppInfo(url=webapp_url))]
    ])
    await message.answer(
        "🚀 <b>ИГРА РАКЕТА</b> 🚀\n\n"
        "Нажми на кнопку, чтобы запустить игру-приложение!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

# ================= ОСНОВНЫЕ КОМАНДЫ =================

@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс", "balance"])
async def balance_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    await message.answer(f"💰 <b>Твой баланс:</b> {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text.lower() in ["профиль", "profile", "статистика", "stats"])
async def profile_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    cursor.execute("SELECT balance, wins, loses, total_bet, total_win FROM users WHERE user_id=?", (uid,))
    u = cursor.fetchone()
    await message.answer(
        f"👤 <b>ПРОФИЛЬ</b>\n\n"
        f"💰 Баланс: <b>{u[0]}</b> DRUNK\n"
        f"🏆 Победы: {u[1]}\n"
        f"💀 Поражения: {u[2]}\n"
        f"📊 Всего игр: {u[1] + u[2]}\n"
        f"💸 Поставлено: {u[3]}\n"
        f"🎉 Выиграно: {u[4]}",
        parse_mode=ParseMode.HTML
    )

@dp.message(lambda m: m.text and m.text.lower() in ["бонус", "bonus"])
async def bonus_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    if can_take_bonus(uid):
        take_bonus(uid)
        await message.answer(f"🎁 <b>+2500 DRUNK</b>\n\n💰 Новый баланс: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
    else:
        await message.answer("⏰ <b>Бонус ещё не доступен!</b>\nПопробуй через 24 часа", parse_mode=ParseMode.HTML)

# ================= ПЕРЕВОДЫ =================

@dp.message(lambda m: m.reply_to_message and m.text and len(m.text.split()) == 2 and m.text.split()[0].lower() in ["п", "перевод", "перевести"])
async def transfer_reply_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    to_user = message.reply_to_message.from_user.id
    if uid == to_user:
        await message.answer("❌ Нельзя перевести самому себе!")
        return
    try:
        amount = int(message.text.split()[1])
        if amount < 10:
            await message.answer("❌ Минимум 10 DRUNK")
            return
        if get_balance(uid) < amount:
            await message.answer(f"❌ Недостаточно средств! Твой баланс: {get_balance(uid)} DRUNK")
            return
        if transfer_money(uid, to_user, amount):
            to_name = get_user_name(to_user)
            await message.answer(f"✅ Переведено {amount} DRUNK пользователю {to_name}\n💎 Твой баланс: {get_balance(uid)} DRUNK")
    except ValueError:
        await message.answer("❌ Пример: <code>п 100</code>", parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and len(m.text.split()) == 3 and m.text.split()[0].lower() in ["п", "перевод", "перевести"] and not m.reply_to_message)
async def transfer_username_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    try:
        parts = message.text.split()
        amount = int(parts[1])
        target = parts[2].replace("@", "")
        cursor.execute("SELECT user_id FROM users WHERE username=?", (target,))
        r = cursor.fetchone()
        if not r:
            await message.answer("❌ Пользователь не найден!")
            return
        to_user = r[0]
        if uid == to_user:
            await message.answer("❌ Нельзя перевести самому себе!")
            return
        if amount < 10:
            await message.answer("❌ Минимум 10 DRUNK")
            return
        if get_balance(uid) < amount:
            await message.answer(f"❌ Недостаточно средств! Твой баланс: {get_balance(uid)} DRUNK")
            return
        if transfer_money(uid, to_user, amount):
            await message.answer(f"✅ Переведено {amount} DRUNK пользователю @{target}\n💎 Твой баланс: {get_balance(uid)} DRUNK")
    except ValueError:
        await message.answer("❌ Пример: <code>п 100 @username</code>", parse_mode=ParseMode.HTML)

@dp.message(lambda m: m.text and m.text.lower() == "топ")
async def top_cmd(message: Message):
    top = get_top_users()
    if not top:
        await message.answer("❌ Нет пользователей!")
        return
    text = "🏆 <b>ТОП ИГРОКОВ</b> 🏆\n\n"
    for i, (uid, balance) in enumerate(top, 1):
        text += f"{i}. {get_user_name(uid)} — {balance} DRUNK\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ================= ИГРЫ =================

@dp.message(lambda m: m.text and m.text.lower().startswith("мины"))
async def mines_start_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    if get_active_game(uid):
        await message.answer("❌ У тебя уже есть активная игра!")
        return
    try:
        parts = message.text.split()
        bet = int(parts[1])
        mines_count = int(parts[2])
    except:
        await message.answer("❌ Использование: <code>мины 100 5</code>", parse_mode=ParseMode.HTML)
        return
    await start_mines(message, bet, mines_count)

@dp.callback_query(F.data.startswith("open_"))
async def mines_open_handler(callback: CallbackQuery):
    cell = int(callback.data.split("_")[1])
    await open_cell(callback, cell)

@dp.callback_query(F.data == "cashout")
async def mines_cashout_handler(callback: CallbackQuery):
    await cashout(callback)

@dp.message(lambda m: m.text and m.text.lower().startswith("слоты"))
async def slots_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    try:
        bet = int(message.text.split()[1])
    except:
        await message.answer("❌ Использование: <code>слоты 100</code>", parse_mode=ParseMode.HTML)
        return
    await play_slots(message, bet)

@dp.message(lambda m: m.text and m.text.lower().startswith("кости"))
async def dice_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    try:
        bet = int(message.text.split()[1])
    except:
        await message.answer("❌ Использование: <code>кости 100</code>", parse_mode=ParseMode.HTML)
        return
    await play_dice(message, bet)

@dp.message(lambda m: m.text and m.text.lower().startswith("баскет"))
async def basketball_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    try:
        parts = message.text.lower().split()
        if len(parts) == 3 and parts[1] in ["лёгкий", "легкий", "easy"]:
            difficulty = "easy"
            bet = int(parts[2])
        elif len(parts) == 3 and parts[1] in ["сложный", "hard"]:
            difficulty = "hard"
            bet = int(parts[2])
        else:
            difficulty = "normal"
            bet = int(parts[1])
    except (ValueError, IndexError):
        await message.answer(
            "❌ <b>БАСКЕТБОЛ - КОМАНДЫ</b>\n\n"
            "🏀 <code>баскет 100</code> - средний (x2.5)\n"
            "🏀 <code>баскет легкий 100</code> - легкий (x1.5)\n"
            "🏀 <code>баскет сложный 100</code> - сложный (x3.5)",
            parse_mode=ParseMode.HTML
        )
        return
    await play_basketball(message, bet, difficulty)

@dp.message(lambda m: m.text and m.text.lower().startswith("пирамида"))
async def pyramid_start_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    try:
        bet = int(message.text.split()[1])
    except:
        await message.answer("❌ Использование: <code>пирамида 100</code>", parse_mode=ParseMode.HTML)
        return
    await start_pyramid(message, bet)

@dp.message(lambda m: m.text and m.text.lower().startswith("ракета"))
async def rocket_start_handler(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    create_user(uid, message.from_user.first_name, message.from_user.username)
    try:
        bet = int(message.text.split()[1])
    except:
        await message.answer("❌ Использование: <code>ракета 100</code>", parse_mode=ParseMode.HTML)
        return
    await start_rocket(message, bet)

# ================= РУЛЕТКА =================

@dp.message(lambda m: m.text and m.text.lower() == "рулетка")
async def roulette_start_handler(message: Message):
    await start_roulette(message)

@dp.message(lambda m: m.text and len(m.text.split()) >= 2 and m.text.split()[0].isdigit())
async def roulette_bet_handler(message: Message):
    uid = message.from_user.id
    text = message.text.strip()
    parts = text.split()
    if text.lower() in ["рулетка", "ставки", "отменить", "го", "крутить", "б", "баланс", "профиль", "бонус", "топ"]:
        return
    if text.lower().startswith("мины") or text.lower().startswith("слоты") or text.lower().startswith("кости") or text.lower().startswith("баскет"):
        return
    if text.startswith('/'):
        return
    try:
        amount = int(parts[0])
        bet_texts = parts[1:]
    except ValueError:
        return
    if amount < 10:
        await message.answer(f"❌ Минимальная ставка: 10 DRUNK", parse_mode=ParseMode.HTML)
        return
    if len(bet_texts) == 0:
        await message.answer(f"❌ Укажи на что ставишь!\nПример: <code>20 5</code>", parse_mode=ParseMode.HTML)
        return
    if uid not in active_roulettes:
        if is_banned(uid):
            await message.answer("❌ Ты забанен!")
            return
        create_user(uid, message.from_user.first_name, message.from_user.username)
        active_roulettes[uid] = {"bets": [], "total": 0}
        await message.answer(
            f"🎡 <b>ИГРА НАЧАТА!</b>\n\n"
            f"💰 Твой баланс: {get_balance(uid)} DRUNK\n"
            f"📝 Команды: СТАВКИ, ОТМЕНИТЬ, КРУТИТЬ",
            parse_mode=ParseMode.HTML
        )
    if len(bet_texts) == 1:
        await add_bet(message, bet_texts[0], amount)
    else:
        await add_mass_bet(message, bet_texts, amount)

@dp.message(lambda m: m.text and m.text.lower() == "ставки")
async def roulette_show_bets_handler(message: Message):
    await show_bets(message)

@dp.message(lambda m: m.text and m.text.lower() == "отменить")
async def roulette_cancel_handler(message: Message):
    await cancel_bets(message)

@dp.message(lambda m: m.text and m.text.lower() in ["го", "go", "старт", "start", "крутить"])
async def roulette_spin_handler(message: Message):
    await spin_roulette(message)

# ================= КНОПКИ РУЛЕТКИ =================

@dp.message(lambda m: m.text and m.text == "📋 СТАВКИ" and is_private_chat(m))
async def roulette_show_bets_btn(message: Message):
    await show_bets(message)

@dp.message(lambda m: m.text and m.text == "💰 УДВОИТЬ" and is_private_chat(m))
async def roulette_double_btn(message: Message):
    uid = message.from_user.id
    if uid in active_roulettes:
        await double_bet(message)
    else:
        await message.answer("❌ Нет активной игры!")

@dp.message(lambda m: m.text and m.text == "🔄 ПОВТОРИТЬ" and is_private_chat(m))
async def roulette_repeat_btn(message: Message):
    uid = message.from_user.id
    if uid in active_roulettes:
        await repeat_bet(message)
    else:
        await message.answer("❌ Нет активной игры!")

@dp.message(lambda m: m.text and m.text == "❌ ОТМЕНИТЬ" and is_private_chat(m))
async def roulette_cancel_btn(message: Message):
    await cancel_bets(message)

@dp.message(lambda m: m.text and m.text == "🎡 КРУТИТЬ" and is_private_chat(m))
async def roulette_go_btn(message: Message):
    await spin_roulette(message)

# ================= ОБРАБОТЧИКИ КНОПОК ПИРАМИДЫ =================

@dp.callback_query(lambda c: c.data.startswith("pyramid_door_"))
async def pyramid_door_handler(callback: CallbackQuery):
    door_index = int(callback.data.split("_")[2])
    await pyramid_door(callback, door_index)

@dp.callback_query(lambda c: c.data == "pyramid_cashout")
async def pyramid_cashout_handler(callback: CallbackQuery):
    await pyramid_cashout(callback)

@dp.callback_query(lambda c: c.data == "pyramid_end")
async def pyramid_end_handler(callback: CallbackQuery):
    await pyramid_end(callback)

# ================= ОБРАБОТЧИКИ КНОПОК РАКЕТЫ =================

@dp.callback_query(lambda c: c.data == "rocket_cashout")
async def rocket_cashout_handler(callback: CallbackQuery):
    await rocket_cashout(callback)

@dp.callback_query(lambda c: c.data == "rocket_stop")
async def rocket_stop_handler(callback: CallbackQuery):
    await rocket_stop(callback)

# ================= АДМИН КОМАНДЫ =================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Нет доступа!")
        return
    await message.answer(
        "👑 <b>АДМИН ПАНЕЛЬ</b> 👑\n\n"
        "👤 <b>Управление пользователями:</b>\n"
        "• <code>/ban 123456789</code> - забанить\n"
        "• <code>/unban 123456789</code> - разбанить\n"
        "• <code>/give 123456789 1000</code> - выдать деньги\n"
        "• <code>/take 123456789 1000</code> - забрать деньги\n"
        "• <code>/setbalance 123456789 5000</code> - установить баланс\n"
        "• <code>/reset 123456789</code> - сбросить пользователя\n\n"
        "🎫 <b>Управление промокодами:</b>\n"
        "• <code>/createpromo НАЗВАНИЕ СУММА ЛИМИТ ЧАСЫ</code> - создать\n"
        "• <code>/delpromo НАЗВАНИЕ</code> - удалить\n"
        "• <code>/promolist</code> - список\n"
        "• <code>/promoinfo НАЗВАНИЕ</code> - информация\n\n"
        "📊 <b>Информация:</b>\n"
        "• <code>/userinfo 123456789</code> - инфо о пользователе\n"
        "• <code>/stats</code> - статистика\n"
        "• <code>/allusers</code> - список пользователей",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("ban"))
async def ban_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.split()[1])
        ban_user(uid)
        await message.answer(f"✅ Пользователь {uid} забанен")
    except:
        await message.answer("❌ /ban 123456789")

@dp.message(Command("unban"))
async def unban_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.split()[1])
        unban_user(uid)
        await message.answer(f"✅ Пользователь {uid} разбанен")
    except:
        await message.answer("❌ /unban 123456789")

@dp.message(Command("give"))
async def give_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        amt = int(parts[2])
        add_balance(uid, amt)
        await message.answer(f"✅ Выдано {amt} DRUNK пользователю {uid}")
    except:
        await message.answer("❌ /give 123456789 1000")

@dp.message(Command("take"))
async def take_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        amt = int(parts[2])
        remove_balance(uid, amt)
        await message.answer(f"✅ Забрано {amt} DRUNK у пользователя {uid}")
    except:
        await message.answer("❌ /take 123456789 1000")

@dp.message(Command("setbalance"))
async def setbalance_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        amt = int(parts[2])
        set_balance(uid, amt)
        await message.answer(f"✅ Баланс пользователя {uid} установлен на {amt} DRUNK")
    except:
        await message.answer("❌ /setbalance 123456789 5000")

@dp.message(Command("reset"))
async def reset_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.split()[1])
        set_balance(uid, 10000)
        cursor.execute("UPDATE users SET wins=0, loses=0, total_bet=0, total_win=0 WHERE user_id=?", (uid,))
        conn.commit()
        await message.answer(f"✅ Пользователь {uid} сброшен")
    except:
        await message.answer("❌ /reset 123456789")

@dp.message(Command("createpromo"))
async def createpromo_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        if len(parts) < 5:
            await message.answer("❌ Использование: <code>/createpromo НАЗВАНИЕ СУММА ЛИМИТ ЧАСЫ</code>", parse_mode=ParseMode.HTML)
            return
        code = parts[1].upper()
        amount = int(parts[2])
        max_uses = int(parts[3])
        hours = int(parts[4])
        if create_promocode(code, amount, max_uses, ADMIN_ID, hours):
            await message.answer(
                f"✅ <b>Промокод создан!</b>\n\n"
                f"🎫 Код: <code>{code}</code>\n"
                f"💰 Сумма: {amount} DRUNK\n"
                f"👥 Макс. использований: {max_uses}\n"
                f"⏰ Действует: {hours} часов",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(f"❌ Промокод <code>{code}</code> уже существует!", parse_mode=ParseMode.HTML)
    except:
        await message.answer("❌ Ошибка! Пример: <code>/createpromo WELCOME 5000 100 24</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("delpromo"))
async def delpromo_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        code = message.text.split()[1].upper()
        if delete_promocode(code):
            await message.answer(f"✅ Промокод <code>{code}</code> удалён", parse_mode=ParseMode.HTML)
        else:
            await message.answer(f"❌ Промокод <code>{code}</code> не найден", parse_mode=ParseMode.HTML)
    except:
        await message.answer("❌ Использование: <code>/delpromo КОД</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("promolist"))
async def promolist_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    promos = get_all_promocodes()
    if not promos:
        await message.answer("📭 Нет промокодов")
        return
    text = "🎫 <b>СПИСОК ПРОМОКОДОВ</b>\n\n"
    for p in promos:
        code, amount, uses, max_uses, _, _, active = p
        status = "🟢" if active else "🔴"
        text += f"{status} <code>{code}</code> - {amount} DRUNK ({uses}/{max_uses})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("promoinfo"))
async def promoinfo_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        code = message.text.split()[1].upper()
        info = get_promocode_info(code)
        if not info:
            await message.answer(f"❌ Промокод <code>{code}</code> не найден", parse_mode=ParseMode.HTML)
            return
        name, amount, uses, max_uses, _, expires_at, active = info
        status = "🟢 АКТИВЕН" if active else "🔴 НЕАКТИВЕН"
        exp_date = time.strftime("%d.%m.%Y %H:%M", time.localtime(expires_at)) if expires_at else "бессрочно"
        await message.answer(
            f"🎫 <b>ПРОМОКОД {name}</b>\n\n"
            f"📊 Статус: {status}\n"
            f"💰 Сумма: {amount} DRUNK\n"
            f"👥 Использований: {uses}/{max_uses}\n"
            f"⏰ Действует до: {exp_date}",
            parse_mode=ParseMode.HTML
        )
    except:
        await message.answer("❌ Использование: <code>/promoinfo КОД</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("userinfo"))
async def userinfo_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.split()[1])
        u = get_user_info(uid)
        if not u:
            await message.answer("❌ Пользователь не найден")
            return
        await message.answer(
            f"👤 ID: {uid}\n"
            f"💰 Баланс: {u[1]} DRUNK\n"
            f"🏆 Побед: {u[2]}\n"
            f"💀 Поражений: {u[3]}\n"
            f"🚫 {'Забанен' if u[5] else 'Активен'}"
        )
    except:
        await message.answer("❌ /userinfo 123456789")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total_users, total_balance, total_bet, total_win = get_user_stats()
    await message.answer(
        f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance} DRUNK\n"
        f"💸 Всего ставок: {total_bet} DRUNK\n"
        f"🎉 Всего выигрышей: {total_win} DRUNK\n"
        f"📈 Профиль казино: {total_bet - total_win} DRUNK",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("allusers"))
async def allusers_cmd(message: Message):
    if message.from_user.id != ADMIN_ID: return
    users = get_all_users()
    text = "📋 <b>Список пользователей:</b>\n\n"
    for i, (uid, first_name, username) in enumerate(users, 1):
        name = f"@{username}" if username else (first_name or f"ID{uid}")
        text += f"{i}. {name}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ================= ПРОМОКОДЫ ДЛЯ ИГРОКОВ =================

@dp.message(lambda m: m.text and m.text.upper().startswith("ПРОМОКОД"))
async def use_promo_cmd(message: Message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: <code>ПРОМОКОД НАЗВАНИЕ</code>", parse_mode=ParseMode.HTML)
            return
        code = parts[1].upper()
        result = use_promocode(code, uid)
        if result == "not_found":
            await message.answer(f"❌ Промокод <code>{code}</code> не найден!", parse_mode=ParseMode.HTML)
        elif result == "inactive":
            await message.answer(f"❌ Промокод <code>{code}</code> деактивирован!", parse_mode=ParseMode.HTML)
        elif result == "expired":
            await message.answer(f"⏰ Промокод <code>{code}</code> просрочен!", parse_mode=ParseMode.HTML)
        elif result == "max_uses":
            await message.answer(f"❌ Промокод <code>{code}</code> использован максимальное число раз!", parse_mode=ParseMode.HTML)
        elif result == "already_used":
            await message.answer(f"❌ Ты уже использовал промокод <code>{code}</code>!", parse_mode=ParseMode.HTML)
        else:
            await message.answer(
                f"🎉 <b>Промокод активирован!</b> 🎉\n\n"
                f"✅ Код: <code>{code}</code>\n"
                f"💰 Получено: +{result} DRUNK\n"
                f"💎 <b>Новый баланс: {get_balance(uid)} DRUNK</b>",
                parse_mode=ParseMode.HTML
            )
    except:
        await message.answer("❌ Ошибка! Пример: <code>ПРОМОКОД WELCOME</code>", parse_mode=ParseMode.HTML)

# ================= ЗАПУСК =================

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 БОТ ЗАПУЩЕН!")
    print(f"✅ Админ ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())