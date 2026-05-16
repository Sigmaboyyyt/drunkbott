import asyncio
import random
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from database import add_balance, remove_balance, add_win, add_lose, add_bet_stat, get_balance, is_banned, create_user
from config import GAME_EMOJI

active_rockets = {}

async def start_rocket(message: Message, bet: int):
    uid = message.from_user.id
    
    if is_banned(uid):
        await message.answer("❌ Ты забанен!")
        return False
    
    create_user(uid, message.from_user.first_name, message.from_user.username)
    
    if bet < 10:
        await message.answer("❌ Минимальная ставка: 10 DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    if get_balance(uid) < bet:
        await message.answer(f"❌ Недостаточно средств!\n💰 Баланс: {get_balance(uid)} DRUNK", parse_mode=ParseMode.HTML)
        return False
    
    remove_balance(uid, bet)
    add_bet_stat(uid, bet)
    
    active_rockets[uid] = {
        "bet": bet,
        "multiplier": 1.00,
        "game_active": True
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 ЗАБРАТЬ", callback_data="rocket_cashout")],
        [InlineKeyboardButton(text="❌ СТОП", callback_data="rocket_stop")]
    ])
    
    await message.answer(
        f"🚀 <b>РАКЕТА ЗАПУЩЕНА!</b> 🚀\n\n"
        f"💰 Ставка: {bet} DRUNK\n"
        f"📈 Множитель: x1.00\n"
        f"💵 Выигрыш: {bet} DRUNK\n\n"
        f"⚠️ Множитель растёт! Нажми ЗАБРАТЬ вовремя!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    asyncio.create_task(fly_rocket(message, uid))

async def fly_rocket(message: Message, uid: int):
    msg = None
    
    while uid in active_rockets and active_rockets[uid]["game_active"]:
        await asyncio.sleep(1.0)
        
        if uid not in active_rockets:
            break
        
        game = active_rockets[uid]
        if not game["game_active"]:
            break
        
        game["multiplier"] += random.uniform(0.05, 0.12)
        
        crash_chance = min(80, int(game["multiplier"] * 7))
        
        if random.randint(1, 100) <= crash_chance:
            game["game_active"] = False
            add_lose(uid, game["bet"])
            
            await message.answer(
                f"💥 <b>РАКЕТА ВЗОРВАЛАСЬ!</b> 💥\n\n"
                f"📈 Множитель был: x{game['multiplier']:.2f}\n"
                f"💸 Потеряно: {game['bet']} DRUNK\n"
                f"💎 Баланс: {get_balance(uid)} DRUNK",
                parse_mode=ParseMode.HTML
            )
            del active_rockets[uid]
            return
        
        win = int(game["bet"] * game["multiplier"])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💰 ЗАБРАТЬ {win} DRUNK", callback_data="rocket_cashout")],
            [InlineKeyboardButton(text="❌ СТОП", callback_data="rocket_stop")]
        ])
        
        try:
            if msg is None:
                msg = await message.answer(
                    f"🚀 <b>РАКЕТА ЛЕТИТ...</b> 🚀\n\n"
                    f"💰 Ставка: {game['bet']} DRUNK\n"
                    f"📈 Множитель: x{game['multiplier']:.2f}\n"
                    f"💵 Выигрыш: {win} DRUNK\n"
                    f"⚠️ Риск: {crash_chance}%",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await msg.edit_text(
                    f"🚀 <b>РАКЕТА ЛЕТИТ...</b> 🚀\n\n"
                    f"💰 Ставка: {game['bet']} DRUNK\n"
                    f"📈 Множитель: x{game['multiplier']:.2f}\n"
                    f"💵 Выигрыш: {win} DRUNK\n"
                    f"⚠️ Риск: {crash_chance}%",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        except:
            pass

async def rocket_cashout(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid not in active_rockets:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_rockets[uid]
    if not game["game_active"]:
        await callback.answer("❌ Игра уже завершена!", show_alert=True)
        return
    
    game["game_active"] = False
    win = int(game["bet"] * game["multiplier"])
    add_balance(uid, win)
    add_win(uid, win)
    
    await callback.message.edit_text(
        f"🎉 <b>ВЫИГРЫШ ЗАБРАН!</b> 🎉\n\n"
        f"💰 Ставка: {game['bet']} DRUNK\n"
        f"📈 Множитель: x{game['multiplier']:.2f}\n"
        f"💵 Выигрыш: +{win} DRUNK\n"
        f"💎 Баланс: {get_balance(uid)} DRUNK",
        parse_mode=ParseMode.HTML
    )
    
    del active_rockets[uid]
    await callback.answer()

async def rocket_stop(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid not in active_rockets:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return
    
    game = active_rockets[uid]
    game["game_active"] = False
    add_lose(uid, game["bet"])
    
    await callback.message.edit_text(
        f"🛑 <b>ИГРА ОСТАНОВЛЕНА</b>\n\n"
        f"💸 Потеряно: {game['bet']} DRUNK\n"
        f"💎 Баланс: {get_balance(uid)} DRUNK",
        parse_mode=ParseMode.HTML
    )
    
    del active_rockets[uid]
    await callback.answer()