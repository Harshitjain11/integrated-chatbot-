# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import re
from datetime import datetime

# ---- Chatbot files ----
from chatbot.model_loader import ModelLoader
from chatbot.intent_predictor import IntentPredictor
from chatbot.entity_extractor import (
    extract_items, extract_booking, extract_order_id
)
from chatbot.session_manager import get_session, dump_sessions
from chatbot.order_manager import (
    create_order_record, get_order, cancel_order,
    create_booking, list_orders_for_user
)
from chatbot.response_generator import choose_response

# ---- Config ----
PREDICTION_THRESHOLD = 0.25

app = Flask(__name__)
CORS(app)

# ---- Load ML ----
model_loader = ModelLoader()
predictor = IntentPredictor(model_loader, threshold=PREDICTION_THRESHOLD)


# =================================================================
#                           CHAT ENDPOINT
# =================================================================
@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({"reply": "Invalid request"}), 400

    user_id = str(payload.get("user_id", "anonymous"))
    message = payload.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please type something."})

    session = get_session(user_id)

    # 0️⃣ If user typed an order ID directly
    possible_oid = extract_order_id(message)
    if possible_oid:
        order = get_order(possible_oid)
        if order:
            items_text = ", ".join([f"{i['qty']}x {i['name']}" for i in order["items"]])
            reply = f"Order #{order['order_id']} — {items_text} — Status: {order['status']}"
            return jsonify({"reply": reply, "intent": "track_order"})

    # 1️⃣ Predict intent
    tag, conf = predictor.predict(message.lower())

    # =================================================================
    #                       INTENT: FALLBACK
    # =================================================================
    if tag == "fallback":
        fb = choose_response("fallback") or "Sorry, I didn't understand."
        return jsonify({"reply": fb, "intent": "fallback", "confidence": conf})

    # =================================================================
    #                       INTENT: NEW ORDER
    # =================================================================
    if tag == "new_order":
        session["temp_order"] = {"items": []}
        session["last_intent"] = "new_order"
        return jsonify({"reply": "Sure! What would you like to order?", "intent": tag})

    # =================================================================
    #                       INTENT: ADD ITEM
    # =================================================================
    # ============================ ADD ITEM =============================
    if tag == "order_item" or session.get("last_intent") == "new_order":

        items = extract_items(message)

        if not items:
            return jsonify({"reply": "I couldn't understand which item to add."})

        # ensure temp_order has items list
        temp = session.get("temp_order", {})

        if "items" not in temp:
            temp["items"] = []

        temp["items"].extend(items)

        session["temp_order"] = temp
        session["last_intent"] = "order_item"

        added_text = ", ".join([f"{it['qty']} x {it['name']}" for it in items])
        return jsonify({"reply": f"Added {added_text}. Say 'confirm' to place order."})

    # =================================================================
    #                       INTENT: REMOVE ITEM
    # =================================================================
    if tag == "remove_item":
        to_remove = extract_items(message)
        temp = session.get("temp_order", {"items": []})
        existing = temp["items"]

        removed = []

        for r in to_remove:
            for e in existing[:]:
                if e["name"].lower() == r["name"].lower():
                    if e["qty"] > r["qty"]:
                        e["qty"] -= r["qty"]
                    else:
                        existing.remove(e)
                    removed.append(r["name"])
                    break

        session["temp_order"]["items"] = existing

        if removed:
            return jsonify({"reply": f"Removed: {', '.join(removed)}"})
        else:
            return jsonify({"reply": "Item not found in your cart."})

    # =================================================================
    #                       INTENT: CONFIRM ORDER
    # =================================================================
    if tag == "confirm_order" or re.search(r"\b(confirm|place|yes)\b", message, re.I):
        items = session.get("temp_order", {}).get("items", [])

        if not items:
            return jsonify({"reply": "Your cart is empty."})

        total = sum(i["qty"] * 99 for i in items)  # demo pricing
        oid, order = create_order_record(user_id, items, total)

        session["temp_order"] = {}
        session["last_intent"] = None

        return jsonify({
            "reply": f"Order placed! ID {oid}. Total ₹{total}. Use 'track {oid}'.",
            "intent": "confirm_order"
        })

    # =================================================================
    #                       INTENT: TRACK ORDER
    # =================================================================
    if tag == "track_order":
        oid = extract_order_id(message)
        if not oid:
            return jsonify({"reply": "Please give an order ID."})

        order = get_order(oid)
        if not order:
            return jsonify({"reply": f"No order found for ID {oid}."})

        items_text = ", ".join([f"{i['qty']}x {i['name']}" for i in order["items"]])
        return jsonify({"reply": f"Order #{oid}: {items_text} — Status: {order['status']}"})

    # =================================================================
    #                       INTENT: CANCEL ORDER
    # =================================================================
    if tag == "cancel_order":
        oid = extract_order_id(message)

        if not oid:
            orders = list_orders_for_user(user_id)
            if orders:
                oid = orders[0]["order_id"]

        if not oid:
            return jsonify({"reply": "Which order should I cancel?"})

        cancel_order(oid)
        return jsonify({"reply": f"Order #{oid} has been cancelled."})

    # =================================================================
    #                       INTENT: TABLE BOOKING
    # =================================================================
    if tag == "book_table":
        b = extract_booking(message)

        people = b.get("people") or 2
        tm = b.get("time") or "19:00"
        dt = b.get("date") or datetime.utcnow().date().isoformat()
        pref = b.get("preference")

        booking = create_booking(user_id, people, dt, tm, pref)

        return jsonify({
            "reply": f"Table booked for {people} at {tm}. Booking ID {booking['booking_id']}.",
            "intent": "book_table"
        })

    # =================================================================
    #                DEFAULT GENERIC RESPONSE
    # =================================================================
    resp = choose_response(tag)
    if resp:
        return jsonify({"reply": resp})

    return jsonify({"reply": "Sorry, I didn't get that."})


# =================================================================
# DEBUG ROUTES
# =================================================================
@app.route("/_sessions")
def debug_sessions():
    return jsonify(dump_sessions())


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
