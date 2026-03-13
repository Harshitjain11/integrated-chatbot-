"""
Enhanced Flask app for FoodIn chatbot backend with ML Integration.
Integrates: OrderManager, ModelLoader, EntityExtractor, ResponseGenerator, SessionManager
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pathlib import Path
import os
import json
from datetime import datetime, date, timedelta
import re
import uuid
from dotenv import load_dotenv

# Import custom modules
try:
    from order_manager import OrderManager
except Exception as e:
    print(f"OrderManager import warning: {e}")
    OrderManager = None

try:
    from model_loader import ModelLoader
except Exception as e:
    print(f"ModelLoader import warning: {e}")
    ModelLoader = None

try:
    from entity_extractor import extract_items, extract_booking, extract_order_id
except Exception as e:
    print(f"EntityExtractor import warning: {e}")
    extract_items = None
    extract_booking = None
    extract_order_id = None

try:
    from response_generator import choose_response
except Exception as e:
    print(f"ResponseGenerator import warning: {e}")
    choose_response = None

try:
    from session_manager import get_session, set_session, clear_temp_order
except Exception as e:
    print(f"SessionManager import warning: {e}")
    get_session = None
    set_session = None
    clear_temp_order = None

try:
    from utils import next_order_id
except Exception as e:
    print(f"Utils import warning: {e}")
    # Fallback order ID generator
    from itertools import count
    _order_counter = count(1000)
    def next_order_id():
        return int(next(_order_counter))

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'database': os.getenv('DB_NAME', 'Dineaus'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'autocommit': False
}

# ---------- Initialize OrderManager ----------
om = None
if OrderManager is not None:
    try:
        om = OrderManager(DB_CONFIG)
        try:
            om.initialize_schema()
            print("✅ OrderManager initialized with MySQL")
        except Exception as e:
            print("Schema init warning:", e)
    except Exception as e:
        print("Warning: Failed to initialize MySQL OrderManager:", e)
        om = None

# In-memory fallback if DB unavailable
class _InMemoryOrderManager:
    def __init__(self):
        self.orders = {}
        self.bookings = {}

    def add_order(self, user_id: str, items):
        order_id = str(next_order_id())
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        total = sum(float(i.get("price", 50)) * int(i.get("qty", 1)) for i in items or [])
        order = {"order_id": order_id, "user_id": user_id, "items": items or [], "total": total,
                 "status": "created", "created_at": now, "updated_at": now}
        self.orders[order_id] = order
        return order_id

    def update_order_items(self, order_id, items):
        if order_id not in self.orders:
            return False
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        total = sum(float(i.get("price", 50)) * int(i.get("qty", 1)) for i in items or [])
        self.orders[order_id]["items"] = items or []
        self.orders[order_id]["total"] = total
        self.orders[order_id]["updated_at"] = now
        return True

    def confirm_order(self, order_id):
        o = self.orders.get(str(order_id))
        if not o:
            return False
        o["status"] = "confirmed"
        o["updated_at"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return True

    def cancel_order(self, order_id, reason=None):
        o = self.orders.get(str(order_id))
        if not o or o.get("status") in ("delivered", "cancelled"):
            return False
        o["status"] = "cancelled"
        o["updated_at"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return True

    def track_order(self, order_id):
        return self.orders.get(str(order_id))

    def book_table(self, user_id, booking_date, time_slot, seats):
        booking_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        b = {"booking_id": booking_id, "user_id": user_id, "booking_date": booking_date,
             "time_slot": time_slot, "seats": seats, "status": "pending",
             "created_at": now, "updated_at": now}
        self.bookings[booking_id] = b
        return booking_id

    def get_booking(self, booking_id):
        return self.bookings.get(booking_id)

    def cancel_booking(self, booking_id):
        b = self.bookings.get(booking_id)
        if not b or b.get("status") == "cancelled":
            return False
        b["status"] = "cancelled"
        b["updated_at"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        return True

if om is None:
    print("⚠️ Using in-memory OrderManager fallback (no MySQL)")
    om = _InMemoryOrderManager()

# ---------- Initialize ML Model ----------
ml_model = None
if ModelLoader is not None:
    try:
        ml_model = ModelLoader()
        print("✅ ML Model loaded successfully")
    except Exception as e:
        print(f"⚠️ Could not load ML model: {e}")
        print("   Using fallback intent detection")

# Sample menu for fuzzy matching
MENU_ITEMS = [
    "pizza", "burger", "pasta", "biryani", "chicken tikka", 
    "naan", "dal makhani", "paneer tikka", "coke", "pepsi",
    "butter chicken", "tandoori chicken", "garlic naan", "roti",
    "samosa", "spring roll", "french fries", "masala dosa"
]

# Menu prices (simple mapping)
MENU_PRICES = {
    "pizza": 250, "burger": 120, "pasta": 180, "biryani": 200,
    "chicken tikka": 220, "naan": 40, "dal makhani": 150,
    "paneer tikka": 200, "coke": 50, "pepsi": 50,
    "butter chicken": 240, "tandoori chicken": 280,
    "garlic naan": 50, "roti": 20, "samosa": 30,
    "spring roll": 80, "french fries": 90, "masala dosa": 120
}

# ---------- Fallback session manager if import fails ----------
if get_session is None:
    _fallback_sessions = {}
    def get_session(user_id):
        if user_id not in _fallback_sessions:
            _fallback_sessions[user_id] = {
                "last_intent": None,
                "temp_order": {"items": []},
                "last_bot_msg": None,
                "created_at": datetime.utcnow().isoformat()
            }
        return _fallback_sessions[user_id]
    
    def set_session(user_id, data):
        _fallback_sessions[user_id] = data
        return data
    
    def clear_temp_order(user_id):
        s = get_session(user_id)
        s["temp_order"] = {"items": []}
        s["last_intent"] = None
        return s

# ---------- Intent prediction using ML model ----------
def predict_intent(text):
    """Use ML model to predict intent, fallback to regex if unavailable"""
    if ml_model:
        try:
            results = ml_model.predict([text])
            intent, confidence = results[0]
            print(f"🤖 ML Prediction: {intent} (confidence: {confidence:.2f})")
            if confidence > 0.35:  # Lower threshold for better coverage
                return intent
        except Exception as e:
            print(f"ML prediction error: {e}")
    
    # Fallback to regex-based intent detection
    return simple_intent_parser(text)

def simple_intent_parser(text: str) -> str:
    """
    Lightweight regex-based intent parser
    Used ONLY when ML confidence is low
    """
    t = text.lower().strip()

    # 1️⃣ Greeting
    if re.search(r'\b(hi|hello|hey|namaste|yo|hi bro|hello bhai)\b', t):
        return "greeting"

    # 2️⃣ Goodbye
    if re.search(r'\b(bye|goodbye|see you|chal bye|milte hain)\b', t):
        return "goodbye"

    # 3️⃣ Thanks
    if re.search(r'\b(thanks|thank you|shukriya|dhanyavaad)\b', t):
        return "thanks"

    # 4️⃣ Menu
    if re.search(r'\b(menu|show menu|menu dikhao|items|food list|kya milega)\b', t):
        return "menu"

    # 5️⃣ Track order
    if re.search(r'\b(track|where|status|kaha hai)\b.*\b(order)\b', t):
        return "track_order"

    # 6️⃣ Confirm order
    if re.search(r'\b(confirm|place order|checkout|final karo|haan confirm)\b', t):
        return "confirm_order"

    # 7️⃣ Cancel order
    if re.search(r'\b(cancel|cancel kar|order hata|nahi chahiye)\b', t):
        return "cancel_order"

    # 8️⃣ Table booking  ✅ FIXED
    if re.search(r'\b(book|reserve|table|booking)\b', t):
        return "book_table"

    # 9️⃣ Remove item
    if re.search(r'\b(remove|delete|hata do|nikal do)\b', t):
        return "remove_item"

    # 🔟 Order / add item  ✅ FIXED
    if re.search(r'\b(add|order|chahiye|get me|i want|le aao|mangao)\b', t):
        return "order_item"

    return "fallback"

# ---------- Frontend route ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- Main chat endpoint ----------
@app.route("/chat", methods=["POST"])
def chat_handler():
    data = request.get_json() or {}
    user_id = data.get("user_id", "anonymous")
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"reply": "Please type something! 😊"}), 200

    # Get user session
    session = get_session(user_id)
    
    # Predict intent
    intent = predict_intent(message)
    session["last_intent"] = intent
    print(f"💭 User: {message}")
    print(f"🎯 Intent: {intent}")
    
    # Try to get response from intents.json first
    bot_response = None
    if choose_response:
        bot_response = choose_response(intent)
    
    # Handle specific intents with dynamic responses
    if intent == "greeting":
        if not bot_response:
            bot_response = "Hi there! 👋 I'm DineBot. I can help you order food, book tables, or track orders. What would you like today?"
    
    elif intent == "goodbye":
        if not bot_response:
            bot_response = "Goodbye! 👋 Come back soon for more delicious food!"
        clear_temp_order(user_id)
    
    elif intent == "thanks":
        if not bot_response:
            bot_response = "You're welcome! 😊 Anything else I can help with?"
    
    elif intent == "menu":
        menu_text = "🍽️ **Our Menu:**\n\n"
        for idx, item in enumerate(MENU_ITEMS[:12], 1):
            price = MENU_PRICES.get(item, 50)
            menu_text += f"{idx}. {item.title()} - ₹{price}\n"
        menu_text += "\n💬 What would you like to order?"
        bot_response = menu_text
    
    elif intent in ("new_order", "order_item"):
        # Extract items using entity extractor
        items = []
        if extract_items:
            items = extract_items(message, menu=MENU_ITEMS)
        else:
            # Fallback: simple extraction
            for menu_item in MENU_ITEMS:
                if menu_item in message.lower():
                    qty = 1
                    # Try to find quantity
                    qty_match = re.search(r'(\d+)\s*' + re.escape(menu_item), message.lower())
                    if qty_match:
                        qty = int(qty_match.group(1))
                    items.append({"name": menu_item, "qty": qty})
        
        if items:
            # Add to session cart
            temp_items = session["temp_order"].get("items", [])
            
            for item in items:
                item["price"] = MENU_PRICES.get(item["name"], 50)
                # Check if item already exists
                existing = next((i for i in temp_items if i["name"] == item["name"]), None)
                if existing:
                    existing["qty"] += item["qty"]
                else:
                    temp_items.append(item)
            
            session["temp_order"]["items"] = temp_items
            
            items_text = ", ".join([f"{i['qty']}x {i['name'].title()}" for i in items])
            cart_summary = "\n".join([f"• {i['qty']}x {i['name'].title()} - ₹{i['price']*i['qty']}" for i in temp_items])
            total = sum(i['price'] * i['qty'] for i in temp_items)
            
            bot_response = f"✅ Added {items_text} to your cart!\n\n**Your Cart:**\n{cart_summary}\n\n**Total: ₹{total}**\n\n💬 Add more items or say 'confirm order' to proceed!"
        else:
            bot_response = "I couldn't find those items. Try saying: '2 pizzas and 1 coke' or type 'menu' to see what we have! 🍕"
    
    elif intent == "remove_item":
        temp_items = session["temp_order"].get("items", [])
        
        if not temp_items:
            bot_response = "Your cart is already empty! 🛒"
        else:
            # Extract items to remove
            items_to_remove = []
            if extract_items:
                items_to_remove = extract_items(message, menu=MENU_ITEMS)
            
            if items_to_remove:
                removed = []
                for item in items_to_remove:
                    temp_items = [i for i in temp_items if i["name"] != item["name"]]
                    removed.append(item["name"].title())
                
                session["temp_order"]["items"] = temp_items
                
                if temp_items:
                    cart_summary = "\n".join([f"• {i['qty']}x {i['name'].title()} - ₹{i['price']*i['qty']}" for i in temp_items])
                    total = sum(i['price'] * i['qty'] for i in temp_items)
                    bot_response = f"✅ Removed {', '.join(removed)}.\n\n**Your Cart:**\n{cart_summary}\n\n**Total: ₹{total}**"
                else:
                    bot_response = "✅ Removed all items. Your cart is now empty! 🛒"
                    clear_temp_order(user_id)
            else:
                # Remove all
                clear_temp_order(user_id)
                bot_response = "✅ Cart cleared! Start fresh with a new order. 🛒"
    
    elif intent == "confirm_order":
        temp_items = session["temp_order"].get("items", [])
        
        if not temp_items:
            bot_response = "Your cart is empty! Add some items first. Type 'menu' to see options. 🍽️"
        else:
            try:
                # Create order
                order_id = om.add_order(user_id, temp_items)
                om.confirm_order(order_id)
                
                total = sum(i["qty"] * i["price"] for i in temp_items)
                items_text = "\n".join([f"• {i['qty']}x {i['name'].title()}" for i in temp_items])
                
                # Clear session cart
                clear_temp_order(user_id)
                session["last_order_id"] = order_id
                
                bot_response = f"🎉 **Order Confirmed!**\n\n📋 Order ID: **{order_id}**\n\n**Items:**\n{items_text}\n\n💰 **Total: ₹{total}**\n\n⏱️ Your order will be ready in 30-40 minutes!\n\n📱 Track your order by saying 'track {order_id}'"
            except Exception as e:
                print(f"Error placing order: {e}")
                bot_response = f"❌ Sorry, there was an error placing your order. Please try again! Error: {str(e)}"
    
    elif intent == "track_order":
        # Extract order ID
        order_id = None
        if extract_order_id:
            order_id = extract_order_id(message)
        else:
            match = re.search(r'\b(\d{4,8})\b', message)
            if match:
                order_id = match.group(1)
        
        # Use last order if no ID specified
        if not order_id and session.get("last_order_id"):
            order_id = session["last_order_id"]
        
        if order_id:
            try:
                order = om.track_order(str(order_id))
                if order:
                    items_text = "\n".join([f"• {i['qty']}x {i['name'].title()}" for i in order.get("items", [])])
                    status_emoji = {"created": "📝", "confirmed": "✅", "preparing": "👨‍🍳", "delivered": "🚚", "cancelled": "❌"}.get(order['status'], "📦")
                    
                    bot_response = f"📦 **Order #{order_id}**\n\n{status_emoji} Status: **{order['status'].upper()}**\n\n**Items:**\n{items_text}\n\n💰 Total: ₹{order.get('total', 0)}"
                else:
                    bot_response = f"❌ Order #{order_id} not found. Please check the order ID and try again."
            except Exception as e:
                print(f"Error tracking order: {e}")
                bot_response = f"❌ Error tracking order: {str(e)}"
        else:
            bot_response = "Please provide your order ID. Example: 'track 1234' 📱"
    
    elif intent == "cancel_order":
        if session.get("last_order_id"):
            try:
                order_id = session["last_order_id"]
                success = om.cancel_order(str(order_id))
                if success:
                    session["last_order_id"] = None
                    bot_response = f"❌ Order #{order_id} has been cancelled successfully."
                else:
                    bot_response = f"⚠️ Cannot cancel order #{order_id}. It may be already delivered or cancelled."
            except Exception as e:
                bot_response = f"❌ Error cancelling order: {str(e)}"
        else:
            bot_response = "No recent order to cancel. 🤷"
    
    elif intent == "book_table":
        booking_info = {}
        if extract_booking:
            booking_info = extract_booking(message)
        
        people = booking_info.get("people")
        time_slot = booking_info.get("time")
        booking_date = booking_info.get("date")
        
        if people and time_slot and booking_date:
            try:
                booking_id = om.book_table(user_id, booking_date, time_slot, people)
                bot_response = f"✅ **Table Booked!**\n\n🆔 Booking ID: {booking_id}\n📅 Date: {booking_date}\n🕐 Time: {time_slot}\n👥 Guests: {people}\n\nSee you soon! 🎉"
            except Exception as e:
                bot_response = f"❌ Error booking table: {str(e)}"
        else:
            missing = []
            if not people: missing.append("number of people")
            if not time_slot: missing.append("time")
            if not booking_date: missing.append("date")
            bot_response = f"To book a table, please provide: {', '.join(missing)}.\n\n📝 Example: 'Book table for 4 people at 7pm tomorrow'"
    
    elif intent == "unknown":
        if not bot_response:
            bot_response = "🤔 I'm not sure I understood that.\n\nYou can:\n• Order food (e.g., '2 pizzas and 1 coke')\n• View our menu\n• Track your order\n• Book a table\n• Ask for help"
    
    # Default fallback
    if not bot_response:
        bot_response = "I'm here to help! Try ordering food, viewing the menu, or booking a table. 😊"
    
    session["last_bot_msg"] = bot_response
    set_session(user_id, session)
    
    print(f"🤖 Bot: {bot_response[:100]}...")
    return jsonify({"reply": bot_response}), 200

# ---------- API Endpoints ----------
@app.route('/api/order/add', methods=['POST'])
def api_add_order():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    items = data.get('items')
    if not user_id or not items:
        return jsonify({'ok': False, 'message': 'user_id and items required'}), 400
    try:
        order_id = om.add_order(user_id, items)
        return jsonify({'ok': True, 'order_id': order_id}), 201
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/order/track/<order_id>', methods=['GET'])
def api_track_order(order_id):
    try:
        order = om.track_order(order_id)
        if not order:
            return jsonify({'ok': False, 'message': 'order not found'}), 404
        return jsonify({'ok': True, 'order': order}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/order/confirm', methods=['POST'])
def api_confirm_order():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'ok': False, 'message': 'order_id required'}), 400
    try:
        ok = om.confirm_order(order_id)
        return jsonify({'ok': ok}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/order/cancel', methods=['POST'])
def api_cancel_order():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'ok': False, 'message': 'order_id required'}), 400
    try:
        ok = om.cancel_order(order_id)
        return jsonify({'ok': ok}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ---------- Health check ----------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'ml_model': ml_model is not None,
        'order_manager': om is not None,
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ---------- Run server ----------
if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    port = int(os.getenv('PORT', 5000))
    print(f"\n🚀 Starting DineBot Server on port {port}...")
    print(f"📊 ML Model: {'✅ Loaded' if ml_model else '⚠️ Using fallback'}")
    print(f"💾 Database: {'✅ MySQL' if isinstance(om, OrderManager) else '⚠️ In-memory'}")
    app.run(host='0.0.0.0', port=port, debug=debug)