import asyncio
import random
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance, is_banned, create_user
from config import GAME_EMOJI

active_pyramids = {}

# Уровни пирамиды
LEVELS = [
    {"level": 1, "name": "1️⃣", "multiplier": 1.2, "win_doors": 2, "total_doors": 4},
    {"level": 2, "name": "2️⃣", "multiplier": 1.5, "win_doors": 2, "total_doors": 4},
    {"level": 3, "name": "3️⃣", "multiplier": 1.7, "win_doors": 2, "total_doors": 4},
    {"level": 4, "name": "4️⃣", "multiplier": 2.0, "win_doors": 1, "total_doors": 4},
    {"level": 5, "name": "5️⃣", "multiplier": 3.5, "win_doors": 1, "total_doors": 4},
    {"level": 6, "name": "6️⃣", "multiplier": 5.0, "win_doors": 1, "total_doors": 4},
    {"level": 7, "name": "7️⃣", "multiplier": 10.0, "win_doors": 1, "total_doors": 4},
]

def get_pyramid_visual(level: int):
    """Визуализация пирамиды"""
    symbols = ["⬜", "🟫", "🟧", "🟨", "🟩", "🟦", "🟪"]
    pyramid = ""
    for i in range(7, 0, -1):
        if i <= level:
            pyramid += f"{symbols[i-1]} УР.{i} ✅ x{LEVELS[i-1]['multiplier']}\n"
        else:
            pyramid += f"⬛ УР.{i} ❓ x{LEVELS[i-1]['multiplier']}\n"
    return pyramid

def create_doors_keyboard():
    """Создаёт клавиатуру с 4 дверьми"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚪 1", callback_data="pyramid_door_0"),
            InlineKeyboardButton(text="🚪 2", callback_data="pyramid_door_1")
        ],
        [
            InlineKeyboardButton(text="🚪 3", callback_data="pyramid_door_2"),
            InlineKeyboardButton(text="🚪 4", callback_data="pyramid_door_3")
        ],
        [
            InlineKeyboardButton(text="💰 ЗАБРАТЬ", callback_data="pyramid_cashout"),
            InlineKeyboardButton(text="🚪 ЗАКОНЧИТЬ", callback_data="pyramid_end")
        ]
    ])
    return keyboard

async def start_pyramid(message: Message, bet: int):
    uid = message.from_user.id
    
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return False
    
    create_user(uid, message.from_user.first_name, message.from_user.username)
    
    if bet < 10:
        await message.answer("❌ Мин. ставка: 10 DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer(f"❌ Недостаточно средств!\n💰 Баланс: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    # Генерируем правильные двери для каждого уровня
    winning_doors = {}
    for lvl in LEVELS:
        all_doors = list(range(lvl["total_doors"]))
        winning_doors[lvl["level"]] = random.sample(all_doors, lvl["win_doors"])
    
    active_pyramids[uid] = {
        "initial_bet": bet,
        "current_level": 1,
        "current_win": 0,
        "status": "active",
        "winning_doors": winning_doors,
        "money_spent": False
    }
    
    pyramid_visual = get_pyramid_visual(1)
    keyboard = create_doors_keyboard()
    level_info = LEVELS[0]
    
    await message.answer(
        f"🏛️ <b>ПИРАМИДА</b> 🏛️\n\n"
        f"{pyramid_visual}\n"
        f"💰 Ставка: {bet} DRUNK\n"
        f"🎯 Множитель: x{level_info['multiplier']}\n\n"
        f"Выбери дверь:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    return True

async def pyramid_door(callback: CallbackQuery, door_index: int):
    uid = callback.from_user.id
    
    if uid not in active_pyramids:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_pyramids[uid]
    current_level = game["current_level"]
    level_info = LEVELS[current_level - 1]
    
    # Если деньги ещё не списаны - списываем при первом действии
    if not game.get("money_spent", False):
        if get_balance(uid) < game["initial_bet"]:
            await callback.answer("❌ Недостаточно средств!", show_alert=True)
            del active_pyramids[uid]
            return
        remove_balance(uid, game["initial_bet"])
        add_bet_stat(uid, game["initial_bet"])
        game["money_spent"] = True
    
    winning_doors = game["winning_doors"][current_level]
    
    await callback.message.edit_text(
        f"🏛️ <b>ПИРАМИДА</b> 🏛️\n\n"
        f"🚪 Открываю дверь {door_index + 1}...",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(1)
    
    if door_index in winning_doors:
        # ПРОХОД
        win_amount = int(game["initial_bet"] * level_info["multiplier"])
        game["current_win"] = win_amount
        
        if current_level >= len(LEVELS):
            # ВЕРШИНА
            add_balance(uid, win_amount)
            add_win(uid, win_amount)
            
            await callback.message.edit_text(
                f"🏛️ <b>ПИРАМИДА</b> 🏆\n\n"
                f"🎉 <b>ПОБЕДА!</b> Вершина достигнута!\n"
                f"🚪 Дверь {door_index + 1} - проход!\n\n"
                f"💰 +{win_amount} DRUNK\n"
                f"⭐ x{level_info['multiplier']}\n"
                f"💎 Баланс: {get_balance(uid)} DRUNK",
                parse_mode=ParseMode.HTML
            )
            del active_pyramids[uid]
            await callback.answer()
            return
        
        # СЛЕДУЮЩИЙ УРОВЕНЬ
        game["current_level"] += 1
        next_level = game["current_level"]
        next_info = LEVELS[next_level - 1]
        
        pyramid_visual = get_pyramid_visual(next_level)
        keyboard = create_doors_keyboard()
        
        await callback.message.edit_text(
            f"🏛️ <b>ПИРАМИДА</b> 🎉\n\n"
            f"{pyramid_visual}\n"
            f"💰 Ставка: {game['initial_bet']} DRUNK\n"
            f"🏆 Выигрыш: {win_amount} DRUNK\n"
            f"🎯 Множитель: x{next_info['multiplier']}\n\n"
            f"⬆️ <b>Уровень {next_level}! Выбери дверь:</b>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    else:
        # ПРОИГРЫШ
        add_lose(uid, game["initial_bet"])
        
        await callback.message.edit_text(
            f"🏛️ <b>ПИРАМИДА</b> 💀\n\n"
            f"💥 <b>ПРОВАЛ!</b> Пирамида рухнула!\n"
            f"🚪 Дверь {door_index + 1} - пустота...\n\n"
            f"💸 Потеряно: {game['initial_bet']} DRUNK\n"
            f"💎 Баланс: {get_balance(uid)} DRUNK",
            parse_mode=ParseMode.HTML
        )
        del active_pyramids[uid]
        await callback.answer()
        return

async def pyramid_cashout(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid not in active_pyramids:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_pyramids[uid]
    
    # Если деньги ещё не списаны - возвращаем ставку без игры
    if not game.get("money_spent", False):
        await callback.message.edit_text(
            f"🏛️ <b>ПИРАМИДА</b> 🚪\n\n"
            f"❌ Игра отменена. Ставка не списана.\n"
            f"💰 Баланс: {get_balance(uid)} DRUNK",
            parse_mode=ParseMode.HTML
        )
        del active_pyramids[uid]
        await callback.answer()
        return
    
    win = game["current_win"]
    
    if win == 0:
        await callback.message.edit_text(
            f"🏛️ <b>ПИРАМИДА</b> 🚪\n\n"
            f"❌ Ты ещё не открыл ни одной двери!\n"
            f"💰 Баланс: {get_balance(uid)} DRUNK",
            parse_mode=ParseMode.HTML
        )
        del active_pyramids[uid]
        await callback.answer()
        return
    
    add_balance(uid, win)
    add_win(uid, win)
    
    await callback.message.edit_text(
        f"🏛️ <b>ПИРАМИДА</b> 🎊\n\n"
        f"✅ <b>ВЫИГРЫШ ЗАБРАН!</b>\n"
        f"💰 +{win} DRUNK\n"
        f"💎 Баланс: {get_balance(uid)} DRUNK",
        parse_mode=ParseMode.HTML
    )
    
    del active_pyramids[uid]
    await callback.answer()

async def pyramid_end(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid not in active_pyramids:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_pyramids[uid]
    
    if not game.get("money_spent", False):
        await callback.message.edit_text(
            f"🏛️ <b>ПИРАМИДА</b> 🚪\n\n"
            f"❌ Игра завершена. Ставка не списана.\n"
            f"💰 Баланс: {get_balance(uid)} DRUNK",
            parse_mode=ParseMode.HTML
        )
        del active_pyramids[uid]
        await callback.answer()
        return
    
    add_lose(uid, game["initial_bet"])
    
    await callback.message.edit_text(
        f"🏛️ <b>ПИРАМИДА</b> 🚪\n\n"
        f"❌ Игра завершена.\n"
        f"💸 Потеряно: {game['initial_bet']} DRUNK\n"
        f"💎 Баланс: {get_balance(uid)} DRUNK",
        parse_mode=ParseMode.HTML
    )
    
    del active_pyramids[uid]
    await callback.answer()