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

# Settings jadvali (bot sozlamalari)
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

# Standart qiymatlarni kiritish (agar bo'sh bo'lsa)
cursor.execute("SELECT COUNT(*) FROM settings")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("password_hash", ""))
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("admin_phone", ""))
    print("⚠️ Settings jadvaliga standart qatorlar qo'shildi. Iltimos, botni ishga tushirib, parol va telefonni sozlang.")

conn.commit()
conn.close()
print("✅ Database ready with settings table.")