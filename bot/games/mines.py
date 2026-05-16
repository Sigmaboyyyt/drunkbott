import random
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance

active_games = {}

def create_mines_keyboard(opened_cells, bombs, game_over=False, win=False):
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            cell_num = i * 5 + j
            if game_over:
                if cell_num in bombs:
                    row.append(InlineKeyboardButton(text="💣", callback_data="no"))
                elif cell_num in opened_cells:
                    row.append(InlineKeyboardButton(text="✅", callback_data="no"))
                else:
                    row.append(InlineKeyboardButton(text="❓", callback_data="no"))
            elif win:
                row.append(InlineKeyboardButton(text="💰", callback_data="no"))
            else:
                if cell_num in opened_cells:
                    row.append(InlineKeyboardButton(text="⭐", callback_data="no"))
                else:
                    row.append(InlineKeyboardButton(text="🔲", callback_data=f"open_{cell_num}"))
        keyboard.append(row)
    
    if not game_over and not win and len(opened_cells) > 0:
        keyboard.append([InlineKeyboardButton(text="💰 ЗАБРАТЬ ВЫИГРЫШ 💰", callback_data="cashout")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def start_mines(message: Message, bet: int, mines_count: int):
    uid = message.from_user.id
    
    if bet < 10:
        await message.answer("❌ Минимальная ставка: 10💰", parse_mode=ParseMode.HTML)
        return False
    
    if mines_count < 1 or mines_count > 24:
        await message.answer("❌ Мины от 1 до 24", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer("❌ Недостаточно средств!", parse_mode=ParseMode.HTML)
        return False
    
    remove_balance(uid, bet)
    add_bet_stat(uid, bet)
    
    bombs = set(random.sample(range(25), mines_count))
    
    active_games[uid] = {
        "bet": bet,
        "mines": mines_count,
        "opened": set(),
        "bombs": bombs,
        "multi": 1.0,
        "message_id": None
    }
    
    keyboard = create_mines_keyboard(set(), bombs)
    
    msg = await message.answer(
        f"💣 <b>МИННОЕ ПОЛЕ</b> 💣\n\n"
        f"💰 Ставка: {bet}\n"
        f"💣 Мин: {mines_count}\n"
        f"🎯 Безопасных: {25 - mines_count}\n"
        f"✨ Множитель: x1.0\n"
        f"💰 Потенциальный выигрыш: {bet}\n\n"
        f"<i>Нажми на клетку 🔲 чтобы открыть</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    active_games[uid]["message_id"] = msg.message_id
    return True

async def open_cell(callback: CallbackQuery, cell: int):
    uid = callback.from_user.id
    
    if uid not in active_games:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_games[uid]
    
    if cell in game["opened"]:
        await callback.answer("❌ Клетка уже открыта!", show_alert=True)
        return
    
    game["opened"].add(cell)
    
    if cell in game["bombs"]:
        add_lose(uid, game["bet"])
        keyboard = create_mines_keyboard(game["opened"], game["bombs"], game_over=True)
        await callback.message.edit_text(
            f"💥 <b>БУМ!</b> 💥\n\n"
            f"💰 Ставка: {game['bet']}\n"
            f"💣 Ты наступил на мину!\n"
            f"💸 Потеряно: {game['bet']}",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        del active_games[uid]
        await callback.answer("💥 Ты проиграл!", show_alert=True)
        return
    
    safe_cells = 25 - game["mines"]
    opened_safe = len(game["opened"])
    
    multi = 1.0
    for i in range(opened_safe):
        multi *= (safe_cells - i) / (25 - i)
    multi = 1 / multi if multi > 0 else 0
    
    game["multi"] = multi
    potential_win = int(game["bet"] * multi)
    
    if opened_safe == safe_cells:
        add_balance(uid, potential_win)
        add_win(uid, potential_win)
        keyboard = create_mines_keyboard(game["opened"], game["bombs"], win=True)
        await callback.message.edit_text(
            f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
            f"💰 Ставка: {game['bet']}\n"
            f"✨ Множитель: x{round(multi, 2)}\n"
            f"🎉 Выигрыш: <b>{potential_win}</b>💰\n"
            f"💎 Новый баланс: {get_balance(uid)}",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        del active_games[uid]
        await callback.answer("🎉 ПОБЕДА!", show_alert=True)
        return
    
    keyboard = create_mines_keyboard(game["opened"], game["bombs"])
    await callback.message.edit_text(
        f"💣 <b>МИННОЕ ПОЛЕ</b> 💣\n\n"
        f"💰 Ставка: {game['bet']}\n"
        f"💣 Мин: {game['mines']}\n"
        f"🎯 Осталось безопасных: {safe_cells - opened_safe}\n"
        f"✨ Множитель: x{round(multi, 2)}\n"
        f"💰 Выигрыш: {potential_win}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer("✅ Безопасно!")

async def cashout(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid not in active_games:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_games[uid]
    
    if len(game["opened"]) == 0:
        await callback.answer("❌ Открой хотя бы 1 клетку!", show_alert=True)
        return
    
    win = int(game["bet"] * game["multi"])
    add_balance(uid, win)
    add_win(uid, win)
    
    keyboard = create_mines_keyboard(game["opened"], game["bombs"], game_over=True)
    await callback.message.edit_text(
        f"💰 <b>ТЫ ЗАБРАЛ ВЫИГРЫШ!</b> 💰\n\n"
        f"💰 Ставка: {game['bet']}\n"
        f"✨ Множитель: x{round(game['multi'], 2)}\n"
        f"🎉 Выигрыш: <b>{win}</b>💰\n"
        f"💎 Новый баланс: {get_balance(uid)}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    del active_games[uid]
    await callback.answer("💰 Выигрыш забран!", show_alert=True)

def get_active_game(user_id):
    return active_games.get(user_id)