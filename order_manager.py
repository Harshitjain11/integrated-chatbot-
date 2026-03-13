# # chatbot/order_manager.py
# import sqlite3
# from pathlib import Path
# from datetime import datetime
# import json

# DB_PATH = Path("data/foodin.db")
# DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# def _get_conn():
#     conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     conn = _get_conn()
#     cur = conn.cursor()
#     # orders: store items as JSON in items_json
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS orders (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         items_json TEXT,
#         total REAL,
#         status TEXT,
#         created_at TEXT
#     )
#     """)
#     # bookings
#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS bookings (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT,
#         people INTEGER,
#         date TEXT,
#         time TEXT,
#         preference TEXT,
#         status TEXT,
#         created_at TEXT
#     )
#     """)
#     conn.commit()
#     conn.close()

# # init on import
# init_db()

# # --- Orders API ---

# def create_order_record(user_id: str, items: list, total: float):
#     """
#     items: list of {"name":..., "qty":...}
#     returns order_id and order dict
#     """
#     conn = _get_conn()
#     cur = conn.cursor()
#     now = datetime.utcnow().isoformat()
#     items_json = json.dumps(items)
#     status = "confirmed - preparing"
#     cur.execute("INSERT INTO orders (user_id, items_json, total, status, created_at) VALUES (?, ?, ?, ?, ?)",
#                 (user_id, items_json, total, status, now))
#     oid = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return oid, get_order(oid)

# def get_order(order_id):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
#     row = cur.fetchone()
#     conn.close()
#     if not row:
#         return None
#     return {
#         "order_id": row["id"],
#         "user_id": row["user_id"],
#         "items": json.loads(row["items_json"]),
#         "total": row["total"],
#         "status": row["status"],
#         "created_at": row["created_at"]
#     }

# def update_order_status(order_id, status):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
#     conn.commit()
#     conn.close()
#     return True

# def cancel_order(order_id):
#     # mark cancelled
#     return update_order_status(order_id, "cancelled")

# def list_orders_for_user(user_id):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
#     rows = cur.fetchall()
#     conn.close()
#     return [get_order(r["id"]) for r in rows]

# # --- Bookings API ---

# def create_booking(user_id, people:int, date_str:str, time_str:str, preference=None):
#     conn = _get_conn()
#     cur = conn.cursor()
#     now = datetime.utcnow().isoformat()
#     status = "booked"
#     cur.execute("INSERT INTO bookings (user_id, people, date, time, preference, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                 (user_id, people, date_str, time_str, preference, status, now))
#     bid = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return get_booking(bid)

# def get_booking(booking_id):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
#     row = cur.fetchone()
#     conn.close()
#     if not row:
#         return None
#     return {
#         "booking_id": row["id"],
#         "user_id": row["user_id"],
#         "people": row["people"],
#         "date": row["date"],
#         "time": row["time"],
#         "preference": row["preference"],
#         "status": row["status"],
#         "created_at": row["created_at"]
#     }

# def cancel_booking(booking_id):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("UPDATE bookings SET status = ? WHERE id = ?", ("cancelled", booking_id))
#     conn.commit()
#     conn.close()
#     return True

# def list_bookings_for_user(user_id):
#     conn = _get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC", (user_id,))
#     rows = cur.fetchall()
#     conn.close()
#     return [get_booking(r["id"]) for r in rows]
# order_manager.py
"""
MySQL-backed OrderManager for FoodIn:
- orders table: stores order_id (UUID), user_id, items(JSON), total, status, created_at, updated_at
- bookings table: stores booking_id (UUID), user_id, booking_date, time_slot, seats, status, created_at, updated_at

Uses mysql-connector-python.
"""

import mysql.connector
from mysql.connector import errorcode
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

class OrderManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self._conn = None
        self._connect()

    def _connect(self):
        try:
            self._conn = mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as err:
            print("MySQL connection error:", err)
            raise

    def close(self):
        if self._conn:
            self._conn.close()

    def initialize_schema(self):
        """Create tables if not exists."""
        TABLES = {}
        TABLES['orders'] = (
            "CREATE TABLE IF NOT EXISTS orders ("
            "  order_id VARCHAR(36) NOT NULL,"
            "  user_id VARCHAR(128),"
            "  items JSON NOT NULL,"
            "  total DECIMAL(10,2) NOT NULL DEFAULT 0.00,"
            "  status VARCHAR(32) NOT NULL,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL,"
            "  PRIMARY KEY (order_id)"
            ") ENGINE=InnoDB"
        )
        TABLES['bookings'] = (
            "CREATE TABLE IF NOT EXISTS bookings ("
            "  booking_id VARCHAR(36) NOT NULL,"
            "  user_id VARCHAR(128),"
            "  booking_date DATE NOT NULL,"
            "  time_slot VARCHAR(50) NOT NULL,"
            "  seats INT NOT NULL,"
            "  status VARCHAR(32) NOT NULL,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL,"
            "  PRIMARY KEY (booking_id)"
            ") ENGINE=InnoDB"
        )

        cursor = self._conn.cursor()
        for name, ddl in TABLES.items():
            try:
                cursor.execute(ddl)
            except mysql.connector.Error as err:
                print(f"Failed creating table {name}: {err}")
                raise
        cursor.close()
        self._conn.commit()

    # ---------- Orders ----------
    def add_order(self, user_id: str, items: List[Dict[str, Any]]) -> str:
        order_id = str(uuid.uuid4())
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        total = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
        items_json = json.dumps(items, default=str)

        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO orders (order_id, user_id, items, total, status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (order_id, user_id, items_json, total, "created", now, now)
            )
            self._conn.commit()
            return order_id
        except Exception as e:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            row['items'] = json.loads(row['items']) if row.get('items') else []
            return row
        finally:
            cursor.close()

    def update_order_items(self, order_id: str, items: List[Dict[str, Any]]) -> bool:
        items_json = json.dumps(items, default=str)
        total = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET items=%s, total=%s, updated_at=%s WHERE order_id=%s",
                (items_json, total, now, order_id)
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def confirm_order(self, order_id: str) -> bool:
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT status FROM orders WHERE order_id=%s", (order_id,))
            row = cursor.fetchone()
            if not row:
                return False
            current = row[0]
            if current in ("created", "pending"):
                cursor.execute("UPDATE orders SET status=%s, updated_at=%s WHERE order_id=%s",
                               ("confirmed", now, order_id))
                self._conn.commit()
                return True
            # if already confirmed or later, still return True (idempotent)
            return True
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status=%s, updated_at=%s WHERE order_id=%s AND status NOT IN (%s,%s)",
                ("cancelled", now, order_id, "delivered", "cancelled")
            )
            if cursor.rowcount == 0:
                return False
            self._conn.commit()
            return True
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def track_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.get_order(order_id)

    # ---------- Bookings ----------
    def book_table(self, user_id: str, booking_date: str, time_slot: str, seats: int) -> str:
        booking_id = str(uuid.uuid4())
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO bookings (booking_id, user_id, booking_date, time_slot, seats, status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (booking_id, user_id, booking_date, time_slot, seats, "pending", now, now)
            )
            self._conn.commit()
            return booking_id
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
            row = cursor.fetchone()
            return row
        finally:
            cursor.close()

    def cancel_booking(self, booking_id: str) -> bool:
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self._conn.cursor()
        try:
            cursor.execute("UPDATE bookings SET status=%s, updated_at=%s WHERE booking_id=%s AND status != %s",
                           ("cancelled", now, booking_id, "cancelled"))
            self._conn.commit()
            return cursor.rowcount > 0
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()
  