import sqlite3
from datetime import datetime
import hashlib

DB_PATH = "database/crm.db"

def _enable_foreign_keys(conn):
    conn.execute("PRAGMA foreign_keys = ON")

# -------------------- Settings --------------------
def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

# -------------------- Clients --------------------
def add_client(name, phone, address):
    conn = sqlite3.connect(DB_PATH)
    _enable_foreign_keys(conn)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clients(name, phone, address) VALUES(?,?,?)", (name, phone, address))
    conn.commit()
    conn.close()

def add_order(client_id, product, amount):
    conn = sqlite3.connect(DB_PATH)
    _enable_foreign_keys(conn)
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("INSERT INTO orders(client_id, product, amount, date) VALUES(?,?,?,?)",
                   (client_id, product, amount, date))
    conn.commit()
    conn.close()

def get_clients():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, address FROM clients")
    clients = cursor.fetchall()
    conn.close()
    return clients

def get_orders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT orders.id, clients.name, clients.phone, clients.address, orders.product, orders.amount, orders.date
    FROM orders
    JOIN clients ON orders.client_id = clients.id
    """)
    orders = cursor.fetchall()
    conn.close()
    return orders

def delete_client(client_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        _enable_foreign_keys(conn)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success, None
    except sqlite3.Error as e:
        return False, str(e)

def delete_order(order_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        _enable_foreign_keys(conn)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success, None
    except sqlite3.Error as e:
        return False, str(e)