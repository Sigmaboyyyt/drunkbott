import sqlite3
import time

conn = sqlite3.connect("casino.db", check_same_thread=False)
cursor = conn.cursor()

# Таблица пользователей
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 10000,
        wins INTEGER DEFAULT 0,
        loses INTEGER DEFAULT 0,
        last_bonus INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        total_bet INTEGER DEFAULT 0,
        total_win INTEGER DEFAULT 0,
        username TEXT,
        first_name TEXT
    )
""")

# Таблица промокодов
cursor.execute("""
    CREATE TABLE IF NOT EXISTS promocodes(
        code TEXT PRIMARY KEY,
        amount INTEGER,
        uses INTEGER DEFAULT 0,
        max_uses INTEGER,
        created_by INTEGER,
        created_at INTEGER,
        expires_at INTEGER,
        is_active INTEGER DEFAULT 1
    )
""")

# Добавление недостающих колонок (если таблица уже существовала)
try:
    cursor.execute("ALTER TABLE promocodes ADD COLUMN created_at INTEGER DEFAULT 0")
except:
    pass

try:
    cursor.execute("ALTER TABLE promocodes ADD COLUMN expires_at INTEGER DEFAULT 0")
except:
    pass

try:
    cursor.execute("ALTER TABLE promocodes ADD COLUMN is_active INTEGER DEFAULT 1")
except:
    pass

# Таблица использованных промокодов
cursor.execute("""
    CREATE TABLE IF NOT EXISTS promocode_uses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        user_id INTEGER,
        used_at INTEGER,
        amount INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        amount INTEGER,
        timestamp INTEGER
    )
""")

conn.commit()

# ================= ОСНОВНЫЕ ФУНКЦИИ =================

def create_user(user_id, first_name=None, username=None):
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    if first_name or username:
        cursor.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", 
                      (first_name, username, user_id))
    conn.commit()

def get_user_name(user_id):
    cursor.execute("SELECT first_name, username FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if r:
        if r[1]:
            return f"@{r[1]}"
        return r[0] or f"ID{user_id}"
    return f"ID{user_id}"

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else 0

def add_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def remove_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def set_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
    conn.commit()

def add_win(user_id, amount=0):
    cursor.execute("UPDATE users SET wins = wins + 1, total_win = total_win + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def add_lose(user_id, amount=0):
    cursor.execute("UPDATE users SET loses = loses + 1, total_bet = total_bet + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def add_bet_stat(user_id, amount):
    cursor.execute("UPDATE users SET total_bet = total_bet + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def ban_user(user_id):
    cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()

def unban_user(user_id):
    cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
    conn.commit()

def is_banned(user_id):
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r and r[0] == 1

def can_take_bonus(user_id):
    cursor.execute("SELECT last_bonus FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if not r or r[0] == 0:
        return True
    return (time.time() - r[0]) >= 86400

def take_bonus(user_id):
    now = int(time.time())
    add_balance(user_id, 2500)
    cursor.execute("UPDATE users SET last_bonus=? WHERE user_id=?", (now, user_id))
    conn.commit()

def transfer_money(from_user, to_user, amount):
    if get_balance(from_user) < amount:
        return False
    remove_balance(from_user, amount)
    add_balance(to_user, amount)
    cursor.execute("INSERT INTO transactions(from_user, to_user, amount, timestamp) VALUES(?,?,?,?)",
                   (from_user, to_user, amount, int(time.time())))
    conn.commit()
    return True

def get_top_users():
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    return cursor.fetchall()

def get_user_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(total_bet) FROM users")
    total_bet = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(total_win) FROM users")
    total_win = cursor.fetchone()[0] or 0
    return total_users, total_balance, total_bet, total_win

def get_user_info(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def get_all_users():
    cursor.execute("SELECT user_id, first_name, username FROM users LIMIT 50")
    return cursor.fetchall()

# ================= ФУНКЦИИ ДЛЯ ПРОМОКОДОВ =================

def create_promocode(code, amount, max_uses, created_by, expires_hours=24):
    """Создать новый промокод"""
    now = int(time.time())
    expires_at = now + (expires_hours * 3600)
    
    try:
        cursor.execute("""
            INSERT INTO promocodes(code, amount, max_uses, created_by, created_at, expires_at, is_active)
            VALUES(?, ?, ?, ?, ?, ?, 1)
        """, (code.upper(), amount, max_uses, created_by, now, expires_at))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_promocode_info(code):
    """Получить информацию о промокоде"""
    cursor.execute("""
        SELECT code, amount, uses, max_uses, created_at, expires_at, is_active 
        FROM promocodes WHERE code=?
    """, (code.upper(),))
    return cursor.fetchone()

def use_promocode(code, user_id):
    """Использовать промокод"""
    code = code.upper()
    now = int(time.time())
    
    cursor.execute("SELECT * FROM promocodes WHERE code=?", (code,))
    promo = cursor.fetchone()
    
    if not promo:
        return "not_found"
    
    # Проверяем количество колонок (для совместимости со старой БД)
    if len(promo) == 5:
        code_name, amount, uses, max_uses, created_by = promo
        is_active = 1
        created_at = 0
        expires_at = 0
    else:
        code_name, amount, uses, max_uses, created_by, created_at, expires_at, is_active = promo
    
    if is_active == 0:
        return "inactive"
    
    if expires_at and now > expires_at:
        cursor.execute("UPDATE promocodes SET is_active=0 WHERE code=?", (code,))
        conn.commit()
        return "expired"
    
    if uses >= max_uses:
        return "max_uses"
    
    cursor.execute("SELECT * FROM promocode_uses WHERE code=? AND user_id=?", (code, user_id))
    if cursor.fetchone():
        return "already_used"
    
    add_balance(user_id, amount)
    
    cursor.execute("UPDATE promocodes SET uses = uses + 1 WHERE code=?", (code,))
    cursor.execute("INSERT INTO promocode_uses(code, user_id, used_at, amount) VALUES(?,?,?,?)",
                   (code, user_id, now, amount))
    conn.commit()
    
    return amount

def delete_promocode(code):
    """Удалить промокод"""
    cursor.execute("UPDATE promocodes SET is_active=0 WHERE code=?", (code.upper(),))
    conn.commit()
    return cursor.rowcount > 0

def get_all_promocodes():
    """Получить все промокоды"""
    try:
        cursor.execute("""
            SELECT code, amount, uses, max_uses, created_at, expires_at, is_active 
            FROM promocodes ORDER BY created_at DESC
        """)
        return cursor.fetchall()
    except:
        # Если нет новых колонок, возвращаем без них
        cursor.execute("SELECT code, amount, uses, max_uses FROM promocodes")
        return [(r[0], r[1], r[2], r[3], 0, 0, 1) for r in cursor.fetchall()]

def get_promocode_usage(code):
    """Получить список использовавших промокод"""
    cursor.execute("""
        SELECT user_id, used_at, amount FROM promocode_uses WHERE code=?
    """, (code.upper(),))
    return cursor.fetchall()