# chatbot/order_manager.py
from datetime import datetime
from .utils import next_order_id

# in-memory orders dict
_orders = {}

def create_order(user_id: str, items: list, total: float):
    """
    items: list of dicts e.g. [{"name":"cheese burger","qty":2}, ...]
    total: numeric
    Returns order_id (int) and order record
    """
    oid = next_order_id()
    items_desc = ", ".join([f"{it.get('qty',1)} x {it.get('name')}" for it in items])
    order = {
        "order_id": oid,
        "user_id": user_id,
        "items": items_desc,
        "items_raw": items,
        "total": float(total),
        "status": "confirmed - preparing",
        "created_at": datetime.utcnow().isoformat()
    }
    _orders[oid] = order
    return oid, order

def get_order(order_id: int):
    return _orders.get(order_id)

def update_order_status(order_id: int, status: str):
    if order_id in _orders:
        _orders[order_id]["status"] = status
        return True
    return False

def dump_orders():
    return dict(_orders)
