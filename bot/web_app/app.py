import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import json

from database import get_balance, add_balance, remove_balance, add_bet_stat, add_win, add_lose

app = FastAPI()

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Хранилище user_id для сессии
user_sessions = {}

@app.get("/rocket")
async def rocket_page(request: Request):
    # Получаем user_id из URL
    user_id = request.query_params.get("user_id")
    if user_id:
        user_sessions["current_user"] = int(user_id)
        print(f"🚀 Пользователь {user_id} открыл игру")
    
    with open(os.path.join(os.path.dirname(__file__), "static", "rocket.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/get_balance")
async def get_balance_handler(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        
        if not user_id:
            user_id = user_sessions.get("current_user", 7878318723)
        
        balance = get_balance(user_id)
        print(f"💰 Баланс {user_id}: {balance}")
        return JSONResponse({"balance": balance})
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return JSONResponse({"balance": 10000})

@app.post("/place_bet")
async def place_bet(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        bet = data.get("bet", 0)
        
        if not user_id:
            user_id = user_sessions.get("current_user", 7878318723)
        
        current_balance = get_balance(user_id)
        if current_balance < bet:
            return JSONResponse({"success": False, "error": "insufficient funds"})
        
        remove_balance(user_id, bet)
        add_bet_stat(user_id, bet)
        new_balance = get_balance(user_id)
        
        print(f"🎲 Ставка {bet} списана. Новый баланс: {new_balance}")
        return JSONResponse({"success": True, "balance": new_balance})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/update_balance")
async def update_balance(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        win = data.get("win", 0)
        bet = data.get("bet", 0)
        
        if not user_id:
            user_id = user_sessions.get("current_user", 7878318723)
        
        if win > 0:
            add_balance(user_id, win)
            add_win(user_id, win)
            print(f"🎉 Выигрыш {win} начислен!")
        else:
            add_lose(user_id, bet)
            print(f"💸 Проигрыш {bet} зафиксирован")
        
        new_balance = get_balance(user_id)
        return JSONResponse({"balance": new_balance, "success": True})
    except Exception as e:
        return JSONResponse({"balance": 10000, "success": False})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Web App сервер запущен на http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)