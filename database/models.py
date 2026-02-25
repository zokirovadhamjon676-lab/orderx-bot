import sqlite3

conn = sqlite3.connect("database/crm.db")
cursor = conn.cursor()

# Clients jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS clients(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT
)
""")

# Orders jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    product TEXT,
    amount INTEGER,
    date TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
)
""")

# Settings jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

# Users jadvali (telefon va full_name ustunlari bilan)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_banned INTEGER DEFAULT 0,
    joined_at TEXT,
    phone TEXT,
    full_name TEXT
)
""")

# Mavjud jadvalga ustunlar qo'shish (agar mavjud bo'lmasa)
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
if 'phone' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
if 'full_name' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")

# Standart settings qiymatlari
cursor.execute("SELECT COUNT(*) FROM settings")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("password_hash", ""))
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("admin_phone", ""))

conn.commit()
conn.close()
print("✅ Database ready.")