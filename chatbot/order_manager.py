# chatbot/order_manager.py
import sqlite3
from pathlib import Path
from datetime import datetime
import json

DB_PATH = Path("data/foodin.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    # orders: store items as JSON in items_json
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        items_json TEXT,
        total REAL,
        status TEXT,
        created_at TEXT
    )
    """)
    # bookings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        people INTEGER,
        date TEXT,
        time TEXT,
        preference TEXT,
        status TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

# init on import
init_db()

# --- Orders API ---

def create_order_record(user_id: str, items: list, total: float):
    """
    items: list of {"name":..., "qty":...}
    returns order_id and order dict
    """
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    items_json = json.dumps(items)
    status = "confirmed - preparing"
    cur.execute("INSERT INTO orders (user_id, items_json, total, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, items_json, total, status, now))
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return oid, get_order(oid)

def get_order(order_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "order_id": row["id"],
        "user_id": row["user_id"],
        "items": json.loads(row["items_json"]),
        "total": row["total"],
        "status": row["status"],
        "created_at": row["created_at"]
    }

def update_order_status(order_id, status):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return True

def cancel_order(order_id):
    # mark cancelled
    return update_order_status(order_id, "cancelled")

def list_orders_for_user(user_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [get_order(r["id"]) for r in rows]

# --- Bookings API ---

def create_booking(user_id, people:int, date_str:str, time_str:str, preference=None):
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    status = "booked"
    cur.execute("INSERT INTO bookings (user_id, people, date, time, preference, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, people, date_str, time_str, preference, status, now))
    bid = cur.lastrowid
    conn.commit()
    conn.close()
    return get_booking(bid)

def get_booking(booking_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "booking_id": row["id"],
        "user_id": row["user_id"],
        "people": row["people"],
        "date": row["date"],
        "time": row["time"],
        "preference": row["preference"],
        "status": row["status"],
        "created_at": row["created_at"]
    }

def cancel_booking(booking_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET status = ? WHERE id = ?", ("cancelled", booking_id))
    conn.commit()
    conn.close()
    return True

def list_bookings_for_user(user_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [get_booking(r["id"]) for r in rows]
