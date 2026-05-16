import asyncio
import random
import re
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance, is_banned, create_user
from config import GAME_EMOJI

active_roulettes = {}
last_bets = {}

def parse_bet(text: str):
    """Парсит текстовую ставку"""
    text = text.lower().strip()
    
    # Число от 0 до 36
    if re.match(r'^\d{1,2}$', text):
        num = int(text)
        if 0 <= num <= 36:
            return {"type": "number", "numbers": [num], "multiplier": 35, "chance": 1, "display": f"{num}"}
    
    # Диапазон чисел
    if re.match(r'^\d{1,2}-\d{1,2}$', text):
        parts = text.split('-')
        n1, n2 = int(parts[0]), int(parts[1])
        if 0 <= n1 <= 36 and 0 <= n2 <= 36 and n1 <= n2:
            nums = list(range(n1, n2+1))
            if len(nums) == 1:
                multiplier = 35
            elif len(nums) == 2:
                multiplier = 17
            elif len(nums) <= 6:
                multiplier = 8
            elif len(nums) <= 12:
                multiplier = 3
            else:
                multiplier = 2
            return {"type": "range", "numbers": nums, "multiplier": multiplier, "chance": len(nums), "display": f"{n1}-{n2}"}
    
    # Цвета
    if text in ["красное", "красный", "red"]:
        reds = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        return {"type": "color", "numbers": reds, "multiplier": 2, "chance": 18, "display": "красное"}
    if text in ["чёрное", "черное", "black"]:
        blacks = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
        return {"type": "color", "numbers": blacks, "multiplier": 2, "chance": 18, "display": "чёрное"}
    
    # Чёт/Нечёт
    if text in ["чёт", "чет", "even"]:
        evens = [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36]
        return {"type": "parity", "numbers": evens, "multiplier": 2, "chance": 18, "display": "чёт"}
    if text in ["нечёт", "нечет", "odd"]:
        odds = [1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35]
        return {"type": "parity", "numbers": odds, "multiplier": 2, "chance": 18, "display": "нечёт"}
    
    return None

def create_result_keyboard(uid: int):
    """Клавиатура с кнопками после игры"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 ПОВТОРИТЬ СТАВКИ", callback_data=f"roulette_repeat_{uid}"),
            InlineKeyboardButton(text="⚡ УДВОИТЬ СТАВКИ", callback_data=f"roulette_double_{uid}")
        ],
        [InlineKeyboardButton(text="🎰 НОВАЯ ИГРА", callback_data=f"roulette_new_{uid}")]
    ])

def get_roulette_reply_keyboard():
    """Reply-клавиатура для управления рулеткой (внизу экрана)"""
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

async def start_roulette(message: Message):
    """Начать игру в рулетку"""
    uid = message.from_user.id
    
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return
    
    create_user(uid, message.from_user.first_name, message.from_user.username)
    
    if uid in active_roulettes:
        game = active_roulettes[uid]
        await message.answer(
            f"🎡 <b>РУЛЕТКА</b>\n\n"
            f"💰 Всего ставок: {len(game['bets'])} на {game['total']} DRUNK\n\n"
            f"👇 Используй кнопки для управления:",
            reply_markup=get_roulette_reply_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        active_roulettes[uid] = {"bets": [], "total": 0}
        
        await message.answer(
            f"🎡 <b>РУЛЕТКА</b>\n\n"
            f"📝 <b>Как делать ставки:</b>\n"
            f"├ <code>20 5</code> - 20 на число 5\n"
            f"├ <code>20 красное</code> - 20 на красное\n"
            f"├ <code>20 0 1-2 2-3 5-6 7</code> - массовая ставка\n\n"
            f"💰 Минимальная ставка: 10 DRUNK\n\n"
            f"👇 Используй кнопки для управления:",
            reply_markup=get_roulette_reply_keyboard(),
            parse_mode=ParseMode.HTML
        )

async def add_bet(message: Message, bet_text: str, amount: int):
    """Добавить одиночную ставку"""
    uid = message.from_user.id
    username = message.from_user.first_name
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры! Напиши ставку чтобы начать, например: <code>20 5</code>", parse_mode=ParseMode.HTML)
        return False
    
    game = active_roulettes[uid]
    
    if amount < 10:
        await message.answer(f"❌ Минимальная ставка: 10 DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < game["total"] + amount:
        await message.answer(f"❌ Недостаточно средств!\n💰 Твой баланс: {get_balance(uid)} DRUNK\n💰 Нужно: {game['total'] + amount} DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    bet_info = parse_bet(bet_text)
    
    if not bet_info:
        await message.answer(
            f"❌ Неизвестная ставка: <b>{bet_text}</b>\n\n"
            f"📝 <b>Примеры:</b>\n"
            f"├ <code>20 5</code> - число 5 (x35)\n"
            f"├ <code>20 красное</code> - красное (x2)\n"
            f"├ <code>20 чёрное</code> - чёрное (x2)\n"
            f"├ <code>20 чёт</code> - чёт (x2)",
            parse_mode=ParseMode.HTML
        )
        return False
    
    game["bets"].append({
        "amount": amount,
        "info": bet_info,
        "text": bet_text
    })
    game["total"] += amount
    
    last_bets[uid] = {"amount": amount, "text": bet_text, "is_mass": False}
    
    await message.answer(
        f"✅ <b>Ставка принята:</b> {username} {amount} DRUNK на {bet_info['display']}",
        parse_mode=ParseMode.HTML
    )
    return True

async def add_mass_bet(message: Message, bet_texts: list, amount: int):
    """Добавить массовую ставку (несколько чисел и диапазонов)"""
    uid = message.from_user.id
    username = message.from_user.first_name
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры! Напиши ставку чтобы начать, например: <code>20 5</code>", parse_mode=ParseMode.HTML)
        return False
    
    game = active_roulettes[uid]
    
    if amount < 10:
        await message.answer(f"❌ Минимальная ставка: 10 DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    total_add = amount * len(bet_texts)
    
    if get_balance(uid) < game["total"] + total_add:
        await message.answer(f"❌ Недостаточно средств!\n💰 Твой баланс: {get_balance(uid)} DRUNK\n💰 Нужно: {game['total'] + total_add} DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    valid_bets = []
    invalid_bets = []
    
    for bet_text in bet_texts:
        bet_info = parse_bet(bet_text)
        if bet_info:
            valid_bets.append(bet_info)
        else:
            invalid_bets.append(bet_text)
    
    if invalid_bets:
        await message.answer(
            f"❌ Неизвестные ставки: {', '.join(invalid_bets[:5])}",
            parse_mode=ParseMode.HTML
        )
        return False
    
    added_bets = []
    for bet_info in valid_bets:
        game["bets"].append({
            "amount": amount,
            "info": bet_info,
            "text": bet_info['display']
        })
        game["total"] += amount
        added_bets.append(f"✅ {username} {amount} DRUNK на {bet_info['display']}")
    
    last_bets[uid] = {"amount": amount, "texts": bet_texts, "is_mass": True}
    
    await message.answer("\n".join(added_bets), parse_mode=ParseMode.HTML)
    return True

async def show_bets(message: Message):
    """Показать все текущие ставки"""
    uid = message.from_user.id
    username = message.from_user.first_name
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры! Напиши ставку чтобы начать, например: <code>20 5</code>", parse_mode=ParseMode.HTML)
        return
    
    game = active_roulettes[uid]
    
    if not game["bets"]:
        await message.answer("📭 Нет активных ставок. Добавь ставку!", parse_mode=ParseMode.HTML)
        return
    
    bets_text = ""
    for i, bet in enumerate(game["bets"], 1):
        bets_text += f"{i}. {username} {bet['amount']} DRUNK на {bet['info']['display']}\n"
    
    await message.answer(
        f"📋 <b>ТЕКУЩИЕ СТАВКИ</b>\n\n{bets_text}\n💰 <b>Всего: {game['total']} DRUNK</b>",
        parse_mode=ParseMode.HTML
    )

async def cancel_bets(message: Message):
    """Отменить все ставки"""
    uid = message.from_user.id
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры!", parse_mode=ParseMode.HTML)
        return
    
    game = active_roulettes[uid]
    
    if not game["bets"]:
        await message.answer("📭 Нет ставок для отмены!", parse_mode=ParseMode.HTML)
        return
    
    game["bets"] = []
    game["total"] = 0
    
    await message.answer(
        f"🎡 ❌ <b>ВСЕ СТАВКИ ОТМЕНЕНЫ</b>\n\n"
        f"💰 Деньги не списаны\n"
        f"💎 Баланс: {get_balance(uid)} DRUNK",
        parse_mode=ParseMode.HTML
    )

async def double_bet(message: Message):
    """Удвоить последнюю ставку (в текущей игре)"""
    uid = message.from_user.id
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры!", parse_mode=ParseMode.HTML)
        return
    
    game = active_roulettes[uid]
    
    if not game["bets"]:
        await message.answer("❌ Нет ставок для удвоения!", parse_mode=ParseMode.HTML)
        return
    
    last_bet = game["bets"][-1]
    new_amount = last_bet["amount"] * 2
    
    total_without_last = game["total"] - last_bet["amount"]
    if get_balance(uid) < total_without_last + new_amount:
        await message.answer(f"❌ Недостаточно средств для удвоения!\n💰 Нужно: {total_without_last + new_amount} DRUNK\n💰 У тебя: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
        return
    
    game["total"] = total_without_last + new_amount
    last_bet["amount"] = new_amount
    
    await message.answer(
        f"💰 <b>СТАВКА УДВОЕНА!</b>\n\n"
        f"🎲 {last_bet['info']['display']}\n"
        f"💰 Новая сумма: <b>{new_amount} DRUNK</b>\n"
        f"📊 Всего: {game['total']} DRUNK",
        parse_mode=ParseMode.HTML
    )

async def repeat_bet(message: Message):
    """Повторить последнюю ставку (добавить такую же в текущую игру)"""
    uid = message.from_user.id
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры!", parse_mode=ParseMode.HTML)
        return
    
    if uid not in last_bets:
        await message.answer("❌ Нет предыдущей ставки для повтора!", parse_mode=ParseMode.HTML)
        return
    
    last = last_bets[uid]
    
    if last.get("is_mass"):
        for bet_text in last["texts"]:
            await add_bet(message, bet_text, last["amount"])
    else:
        await add_bet(message, last["text"], last["amount"])

async def spin_roulette(message: Message):
    """Запустить рулетку"""
    uid = message.from_user.id
    username = message.from_user.first_name
    
    if uid not in active_roulettes:
        await message.answer("❌ Нет активной игры! Напиши ставку чтобы начать, например: <code>20 5</code>", parse_mode=ParseMode.HTML)
        return
    
    game = active_roulettes[uid]
    
    if not game["bets"]:
        await message.answer("❌ Нет ставок! Добавь ставки перед запуском.", parse_mode=ParseMode.HTML)
        return
    
    total_bet = game["total"]
    
    if get_balance(uid) < total_bet:
        await message.answer(f"❌ Недостаточно средств!\n💰 Нужно: {total_bet} DRUNK, у тебя: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
        return
    
    # Списываем деньги
    remove_balance(uid, total_bet)
    add_bet_stat(uid, total_bet)
    
    # Отправляем GIF анимацию (если есть файл)
    try:
        roulette_animation = FSInputFile("roleta.gif.mp4")
        await message.answer_video(
            roulette_animation, 
            caption=f"🎡 <b>РУЛЕТКА КРУТИТСЯ...</b>", 
            parse_mode=ParseMode.HTML
        )
    except:
        await message.answer(f"🎡 <b>РУЛЕТКА КРУТИТСЯ...</b>", parse_mode=ParseMode.HTML)
    
    await asyncio.sleep(2)
    
    # Генерируем результат
    number = random.randint(0, 36)
    
    if number == 0:
        color_emoji = "🟢"
        color_name = "ЗЕЛЁНОЕ"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        color_emoji = "🔴"
        color_name = "КРАСНОЕ"
    else:
        color_emoji = "⚫"
        color_name = "ЧЁРНОЕ"
    
    field = f"🎯 <b>ВЫПАЛО: {number} {color_emoji}</b>\n"
    
    all_bets_text = ""
    total_win = 0
    win_details = []
    
    for bet in game["bets"]:
        info = bet["info"]
        amt = bet["amount"]
        all_bets_text += f"├ {username} {amt} DRUNK на {info['display']}\n"
        if number in info["numbers"]:
            win_amt = amt * info["multiplier"]
            total_win += win_amt
            win_details.append(f"✅ {info['display']} — выиграл {win_amt} DRUNK (x{info['multiplier']})")
    
    result_text = f"🎡 <b>РЕЗУЛЬТАТ РУЛЕТКИ</b>\n\n"
    result_text += f"{field}\n"
    result_text += f"🎨 Цвет: {color_name} {color_emoji}\n"
    result_text += f"📊 Чётность: {'ЧЁТ' if number % 2 == 0 and number != 0 else 'НЕЧЁТ' if number != 0 else 'НУЛЬ'}\n\n"
    result_text += f"📋 <b>ТВОИ СТАВКИ:</b>\n{all_bets_text}\n"
    
    if win_details:
        result_text += f"✨ <b>ВЫИГРЫШНЫЕ СТАВКИ:</b>\n" + "\n".join(win_details) + "\n\n"
    
    if total_win > 0:
        add_balance(uid, total_win)
        add_win(uid, total_win)
        result_text += f"💰 <b>ВЫИГРЫШ: +{total_win} DRUNK</b>\n"
    else:
        add_lose(uid, total_bet)
        result_text += f"❌ <b>ПРОИГРЫШ: -{total_bet} DRUNK</b>\n"
    
    result_text += f"\n💎 <b>ТВОЙ БАЛАНС: {get_balance(uid)} DRUNK</b>"
    
    # Сохраняем последнюю игру для кнопок (делаем копию)
    last_bets[uid] = {
        "bets": [bet.copy() for bet in game["bets"]],
        "total": total_bet
    }
    
    del active_roulettes[uid]
    
    # Отправляем результат с кнопками
    keyboard = create_result_keyboard(uid)
    await message.answer(result_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)