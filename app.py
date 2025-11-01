# app.py
from flask import Flask, request, jsonify
from flask import render_template
from flask_cors import CORS
from pathlib import Path
import re

from chatbot.model_loader import ModelLoader
from chatbot.intent_predictor import IntentPredictor
from chatbot.entity_extractor import extract_order_id, extract_quantity, extract_item_name
from chatbot.session_manager import get_session, clear_temp_order, dump_sessions
from chatbot.order_manager import create_order, get_order, dump_orders
from chatbot.response_generator import choose_response

# config
MODEL_DIR = Path("data")
PREDICTION_THRESHOLD = 0.45

app = Flask(__name__)
CORS(app)

# initialize model loader + predictor
model_loader = ModelLoader()
predictor = IntentPredictor(model_loader, threshold=PREDICTION_THRESHOLD)

# ---------- Chat endpoint ----------
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON"}), 400

    user_id = str(payload.get("user_id", "anonymous"))
    message = str(payload.get("message", "")).strip()
    if message == "":
        return jsonify({"reply": "Please type something so I can help.", "intent": None})

    session = get_session(user_id)

    # quick extract: if user sends an order id directly, check orders
    possible_oid = extract_order_id(message)
    if possible_oid:
        order = get_order(possible_oid)
        if order:
            reply = f"Order #{possible_oid} — {order['items']} — Status: {order['status']}"
            return jsonify({"reply": reply, "intent": "track_order", "confidence": 0.99})

    # predict intent
    tag, conf = predictor.predict(message)

    # fallback handling
    if tag == "fallback":
        # small heuristics to help
        if "track" in message.lower() and possible_oid:
            order = get_order(possible_oid)
            if order:
                reply = f"Order #{possible_oid}: {order['items']} — Status: {order['status']}"
                return jsonify({"reply": reply, "intent": "track_order", "confidence": 0.99})
        fallback_text = choose_response("fallback") or "I didn't get that. I can help with ordering or tracking orders. Try 'order' or 'track <order_id>'."
        session["last_intent"] = "fallback"
        session["last_bot_msg"] = fallback_text
        return jsonify({"reply": fallback_text, "intent": "fallback", "confidence": conf})

    # NEW ORDER flow
    if tag == "new_order":
        session["last_intent"] = "new_order"
        session["temp_order"] = {"items": [], "restaurant": None}
        reply = choose_response("new_order") or "Sure — what would you like to order?"
        session["last_bot_msg"] = reply
        return jsonify({"reply": reply, "intent": "new_order", "confidence": conf})

    # ITEM ADDED (order_item) or user continuing after new_order
    if tag == "order_item" or session.get("last_intent") == "new_order":
        qty = extract_quantity(message) or 1
        item = extract_item_name(message) or "item"
        temp = session.get("temp_order", {"items": []})
        temp_items = temp.get("items", [])
        temp_items.append({"name": item, "qty": qty})
        temp["items"] = temp_items
        session["temp_order"] = temp
        session["last_intent"] = "order_item"
        reply = f"Added {qty} x {item} to your cart. Say 'confirm' to place order or add more items."
        session["last_bot_msg"] = reply
        return jsonify({"reply": reply, "intent": "order_item", "confidence": conf})

    # CONFIRM ORDER (detect via intent or keywords)
    if tag == "confirm_order" or re.search(r"\b(confirm|place order|yes confirm|place it|confirm order)\b", message, flags=re.I):
        temp = session.get("temp_order") or {}
        items = temp.get("items", [])
        if not items:
            reply = "There are no items in your cart. Tell me what you want to order."
            session["last_bot_msg"] = reply
            return jsonify({"reply": reply, "intent": "confirm_order", "confidence": conf})
        # naive pricing: 99 per item (demo). Replace with DB price lookup later.
        total = sum(it.get("qty",1) * 99 for it in items)
        oid, order = create_order(user_id, items, total)
        # clear temp order
        session["temp_order"] = {}
        session["last_intent"] = None
        reply = f"Order placed! Your order id is {oid}. Total ₹{total:.2f}. Use 'track {oid}' to follow progress."
        session["last_bot_msg"] = reply
        return jsonify({"reply": reply, "intent": "confirm_order", "order_id": oid, "confidence": 0.99})

    # TRACK ORDER flow
    if tag == "track_order":
        oid = extract_order_id(message)
        if not oid:
            ask = choose_response("track_order") or "Please provide your order id (e.g., 1001)."
            session["last_bot_msg"] = ask
            session["last_intent"] = "track_order"
            return jsonify({"reply": ask, "intent": "track_order", "confidence": conf})
        order = get_order(oid)
        if not order:
            reply = f"I couldn't find order #{oid}. Please check the ID."
            session["last_bot_msg"] = reply
            return jsonify({"reply": reply, "intent": "track_order", "confidence": conf})
        reply = f"Order #{oid}: {order['items']} — Status: {order['status']} (placed {order['created_at']})"
        session["last_bot_msg"] = reply
        session["last_intent"] = None
        return jsonify({"reply": reply, "intent": "track_order", "order": order, "confidence": 0.99})

    # Generic mapped responses (greeting, thanks, about_site, goodbye, etc.)
    resp = choose_response(tag)
    if resp:
        session["last_bot_msg"] = resp
        session["last_intent"] = tag
        return jsonify({"reply": resp, "intent": tag, "confidence": conf})

    # final fallback
    fb = choose_response("fallback") or "Sorry, I couldn't process that."
    session["last_bot_msg"] = fb
    session["last_intent"] = "fallback"
    return jsonify({"reply": fb, "intent": "fallback", "confidence": conf})

# debug routes
@app.route("/_sessions", methods=["GET"])
def _sessions():
    return jsonify({"sessions": dump_sessions()})

@app.route("/_orders", methods=["GET"])
def _orders():
    return jsonify({"orders": dump_orders()})
from flask import render_template

@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
