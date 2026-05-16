import asyncio
from aiogram.types import Message
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance
from config import GAME_EMOJI

dice_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

async def play_dice(message: Message, bet: int):
    uid = message.from_user.id
    
    if bet < 10:
        await message.answer(f"{GAME_EMOJI['warning']} Минимальная ставка: 10 {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer(f"{GAME_EMOJI['warning']} Недостаточно средств!\n💰 Баланс: {get_balance(uid)} {GAME_EMOJI['money']}", parse_mode=ParseMode.HTML)
        return False
    
    remove_balance(uid, bet)
    add_bet_stat(uid, bet)
    
    start_msg = await message.answer(
        f"{GAME_EMOJI['dice']} <b>КОСТИ</b> {GAME_EMOJI['dice']}\n\n"
        f"🎲 <i>Бросаем кубики...</i>\n\n"
        f"💰 Ставка: <b>{bet}</b> {GAME_EMOJI['money']}\n"
        f"💎 Баланс: {get_balance(uid)} {GAME_EMOJI['diamond']}",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(1)
    
    dice1 = await message.answer_dice(emoji="🎲")
    a = dice1.dice.value
    
    await asyncio.sleep(0.5)
    
    dice2 = await message.answer_dice(emoji="🎲")
    b = dice2.dice.value
    
    await asyncio.sleep(0.5)
    await start_msg.delete()
    
    if a > b:
        win = bet * 2
        add_balance(uid, win)
        add_win(uid, win)
        
        await message.answer(
            f"{GAME_EMOJI['dice']} <b>КОСТИ</b> {GAME_EMOJI['happy']}\n\n"
            f"┌─────────────────────────┐\n"
            f"│   {dice_emoji[a-1]}  vs  {dice_emoji[b-1]}   │\n"
            f"└─────────────────────────┘\n\n"
            f"🎉 <b>ПОБЕДА!</b> 🎉\n"
            f"🎲 Твой бросок: <b>{a}</b>\n"
            f"🤖 Бросок бота: <b>{b}</b>\n"
            f"✨ Разница: <b>{a - b}</b>\n\n"
            f"{GAME_EMOJI['money']} Выигрыш: <b>+{win}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}",
            parse_mode=ParseMode.HTML
        )
    elif a == b:
        add_balance(uid, bet)
        
        await message.answer(
            f"{GAME_EMOJI['dice']} <b>КОСТИ</b> {GAME_EMOJI['dice']}\n\n"
            f"┌─────────────────────────┐\n"
            f"│   {dice_emoji[a-1]}  vs  {dice_emoji[b-1]}   │\n"
            f"└─────────────────────────┘\n\n"
            f"🤝 <b>НИЧЬЯ!</b> 🤝\n"
            f"🎲 Твой бросок: <b>{a}</b>\n"
            f"🤖 Бросок бота: <b>{b}</b>\n\n"
            f"{GAME_EMOJI['money']} Ставка возвращена\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}",
            parse_mode=ParseMode.HTML
        )
    else:
        add_lose(uid, bet)
        
        await message.answer(
            f"{GAME_EMOJI['dice']} <b>КОСТИ</b> {GAME_EMOJI['sad']}\n\n"
            f"┌─────────────────────────┐\n"
            f"│   {dice_emoji[a-1]}  vs  {dice_emoji[b-1]}   │\n"
            f"└─────────────────────────┘\n\n"
            f"❌ <b>ПРОИГРЫШ!</b> ❌\n"
            f"🎲 Твой бросок: <b>{a}</b>\n"
            f"🤖 Бросок бота: <b>{b}</b>\n"
            f"💀 Разница: <b>{b - a}</b>\n\n"
            f"{GAME_EMOJI['money']} Потеряно: <b>{bet}</b>\n"
            f"{GAME_EMOJI['diamond']} Баланс: {get_balance(uid)}\n\n"
            f"{GAME_EMOJI['luck']} <i>Удача в следующий раз!</i>",
            parse_mode=ParseMode.HTML
        )
    
    return True