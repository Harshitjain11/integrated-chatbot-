# chatbot/session_manager.py
from datetime import datetime

_sessions = {}

def get_session(user_id: str):
    s = _sessions.get(user_id)
    if s is None:
        s = {
            "last_intent": None,
            "temp_order": {},    # e.g. {"items":[{"name":"pizza","qty":1}], "restaurant":None}
            "last_bot_msg": None,
            "created_at": datetime.utcnow().isoformat()
        }
        _sessions[user_id] = s
    return s

def set_session(user_id: str, data: dict):
    _sessions[user_id] = data
    return _sessions[user_id]

def clear_temp_order(user_id: str):
    s = get_session(user_id)
    s["temp_order"] = {}
    s["last_intent"] = None
    return s

def dump_sessions():
    """Return shallow copy for debugging"""
    return dict(_sessions)
