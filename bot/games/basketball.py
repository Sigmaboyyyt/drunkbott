import asyncio
from aiogram.types import Message
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance
from config import GAME_EMOJI

async def play_basketball(message: Message, bet: int, difficulty: str = "normal"):
    uid = message.from_user.id
    
    if bet < 10:
        await message.answer(f"{GAME_EMOJI['warning']} Минимальная ставка: 10 {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer(f"{GAME_EMOJI['warning']} Недостаточно средств!\n💰 Баланс: {get_balance(uid)} {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    if difficulty == "easy":
        multiplier = 1.5
        name = "ЛЁГКИЙ"
        emoji = "🟢"
    elif difficulty == "hard":
        multiplier = 3.5
        name = "СЛОЖНЫЙ"
        emoji = "🔴"
    else:
        multiplier = 2.5
        name = "СРЕДНИЙ"
        emoji = "🟡"
    
    remove_balance(uid, bet)
    add_bet_stat(uid, bet)
    
    start_msg = await message.answer(
        f"{GAME_EMOJI['basketball']} <b>БАСКЕТБОЛ</b> {emoji} {name}\n\n"
        f"🏀 <i>Бросаем мяч...</i>\n\n"
        f"💰 Ставка: <b>{bet}</b> {GAME_EMOJI['money']}\n"
        f"⭐ Множитель: <b>x{multiplier}</b>\n"
        f"💎 Баланс: {get_balance(uid)} {GAME_EMOJI['diamond']}",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(1.5)
    
    basketball = await message.answer_dice(emoji="🏀")
    result = basketball.dice.value
    
    await asyncio.sleep(0.5)
    await start_msg.delete()
    
    required = 4 if difficulty == "normal" else (3 if difficulty == "easy" else 5)
    is_hit = result >= required
    
    if is_hit:
        win = int(bet * multiplier)
        add_balance(uid, win)
        add_win(uid, win)
        
        await message.answer(
            f"{GAME_EMOJI['basketball']} <b>БАСКЕТБОЛ</b> {emoji} {name}\n\n"
            f"✨ <b>ПОПАДАНИЕ!</b> ✨\n"
            f"🏀 → 🧺 <b>ПОПАЛ!</b>\n\n"
            f"🎉 <b>ПОБЕДА!</b> 🎉\n"
            f"🏀 Результат: <b>{result}/5</b>\n"
            f"⭐ Множитель: <b>x{multiplier}</b>\n\n"
            f"{GAME_EMOJI['money']} Выигрыш: <b>+{win}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}",
            parse_mode=ParseMode.HTML
        )
    else:
        add_lose(uid, bet)
        
        await message.answer(
            f"{GAME_EMOJI['basketball']} <b>БАСКЕТБОЛ</b> {emoji} {name}\n\n"
            f"❌ <b>ПРОМАХ!</b> ❌\n"
            f"🏀 → 💥 <b>МИМО!</b>\n\n"
            f"💀 <b>ПРОИГРЫШ!</b> 💀\n"
            f"🏀 Результат: <b>{result}/5</b>\n\n"
            f"{GAME_EMOJI['money']} Потеряно: <b>{bet}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}\n\n"
            f"{GAME_EMOJI['luck']} <i>В следующий раз получится!</i>",
            parse_mode=ParseMode.HTML
        )
    
    return True