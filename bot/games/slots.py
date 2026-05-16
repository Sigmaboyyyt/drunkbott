import asyncio
import random
from aiogram.types import Message
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance
from config import GAME_EMOJI

def get_slot_result(dice_value):
    if dice_value <= 35:
        return "💀", 0, "❌ ПРОИГРЫШ"
    elif dice_value <= 54:
        return "🍒", 1.1, "🍒 МАЛЕНЬКИЙ ВЫИГРЫШ"
    elif dice_value <= 63:
        return "🍊", 1.8, "🍊 СРЕДНИЙ ВЫИГРЫШ"
    else:
        return "7️⃣", 10, f"{GAME_EMOJI['jackpot']} ДЖЕКПОТ! {GAME_EMOJI['jackpot']}"

async def play_slots(message: Message, bet: int):
    uid = message.from_user.id
    
    if bet < 10:
        await message.answer(f"{GAME_EMOJI['warning']} Минимальная ставка: 10 {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer(f"{GAME_EMOJI['warning']} Недостаточно средств!\n💰 Твой баланс: {get_balance(uid)} {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    remove_balance(uid, bet)
    add_bet_stat(uid, bet)
    
    start_msg = await message.answer(
        f"{GAME_EMOJI['slots']} <b>СЛОТЫ</b> {GAME_EMOJI['slots']}\n\n"
        f"🔄 <i>Барабаны крутятся...</i>\n\n"
        f"💰 Ставка: <b>{bet}</b> {GAME_EMOJI['money']}\n"
        f"💎 Баланс: {get_balance(uid)} {GAME_EMOJI['diamond']}",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(1)
    
    dice_msg = await message.answer_dice(emoji="🎰")
    result_value = dice_msg.dice.value
    
    await asyncio.sleep(1.5)
    await start_msg.delete()
    
    symbol, multiplier, win_type = get_slot_result(result_value)
    
    # Красивая визуализация барабанов
    if result_value == 64:
        slots_view = "✨ 7️⃣ | 7️⃣ | 7️⃣ ✨"
    elif result_value >= 55:
        slots_view = "🍊 | 🍊 | 🍊"
    elif result_value >= 36:
        slots_view = "🍒 | 🍒 | 🍒"
    else:
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
        rand = random.choices(symbols, k=3)
        slots_view = f"{rand[0]} | {rand[1]} | {rand[2]}"
    
    if multiplier > 0:
        win = int(bet * multiplier)
        add_balance(uid, win)
        add_win(uid, win)
        
        await message.answer(
            f"{GAME_EMOJI['slots']} <b>СЛОТЫ</b> {GAME_EMOJI['slots']}\n\n"
            f"┌─────────────────────────┐\n"
            f"│     {slots_view}     │\n"
            f"└─────────────────────────┘\n\n"
            f"✨ {win_type} ✨\n"
            f"{GAME_EMOJI['star']} Множитель: <b>x{multiplier}</b>\n"
            f"{GAME_EMOJI['money']} Выигрыш: <b>+{win}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}\n\n"
            f"🎯 Результат: {result_value}/64",
            parse_mode=ParseMode.HTML
        )
    else:
        add_lose(uid, bet)
        
        await message.answer(
            f"{GAME_EMOJI['slots']} <b>СЛОТЫ</b> {GAME_EMOJI['sad']}\n\n"
            f"┌─────────────────────────┐\n"
            f"│     {slots_view}     │\n"
            f"└─────────────────────────┘\n\n"
            f"{win_type}\n"
            f"{GAME_EMOJI['money']} Потеряно: <b>{bet}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}\n\n"
            f"🎯 Результат: {result_value}/64\n"
            f"{GAME_EMOJI['luck']} <i>В следующий раз повезёт!</i>",
            parse_mode=ParseMode.HTML
        )
    
    return True