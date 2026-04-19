from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random, re, time, datetime, ast, operator, os, threading
from zoneinfo import ZoneInfo

# ✅ SAFE RAZORPAY IMPORT
try:
    import razorpay
    RZP_ENABLED = True
except:
    RZP_ENABLED = False

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

lock = threading.Lock()

# ================= MEMORY SYSTEM =================
memory = {
    "facts": {},
    "mood": "neutral",
    "mode": "normal",
    "last_message": "",
    "chat_history": [],
    "learned": {},
    "pin": None,
    "locked": False,
    "stats": {"messages": 0},
    "game": None
}

todos = []
notes = []
start_time = time.time()

# ================= SAFE MATH =================
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv
}

def safe_eval(expr):
    try:
        node = ast.parse(expr, mode='eval').body

        def eval_node(n):
            if isinstance(n, ast.Constant):
                return n.value
            elif isinstance(n, ast.BinOp):
                return operators[type(n.op)](eval_node(n.left), eval_node(n.right))
            else:
                raise Exception("Invalid")

        return eval_node(node)
    except:
        return None

# ================= GREETING =================
def time_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12: return "Good Morning 🌅"
    elif 12 <= hour < 17: return "Good Afternoon ☀️"
    elif 17 <= hour < 21: return "Good Evening 🌇"
    else: return "Good Night 🌙"

def random_greeting():
    return random.choice(["Hey 😄","Hello 👋","Yo 😎","Hi 👋","Welcome 😁","Namaste 🙏"])

# ================= EMOTION =================
def detect_emotion(msg):
    msg = msg.lower()
    if any(w in msg for w in ["sad","cry","bad","upset"]): return "sad"
    if any(w in msg for w in ["happy","good","love"]): return "happy"
    if any(w in msg for w in ["angry","mad"]): return "angry"
    if "bored" in msg: return "bored"
    return "neutral"

# ================= COUNTRY TIME =================
def get_country_time(msg):
    msg = msg.lower()

    timezones = {
        "india": "Asia/Kolkata",
        "uk": "Europe/London",
        "london": "Europe/London",
        "usa": "America/New_York",
        "new york": "America/New_York",
        "california": "America/Los_Angeles",
        "japan": "Asia/Tokyo",
        "china": "Asia/Shanghai",
        "dubai": "Asia/Dubai",
        "pakistan": "Asia/Karachi",
        "australia": "Australia/Sydney"
    }

    for country, zone in timezones.items():
        if country in msg:
            now = datetime.datetime.now(ZoneInfo(zone))
            return f"🕒 Time in {country.title()}: {now.strftime('%H:%M:%S')}"

    return None

# ================= SMART AI =================
def smart_reply(msg):
    msg_lower = msg.lower()

    if re.fullmatch(r"(hi|hello|hey|yo)+", msg_lower):
        return f"{time_greeting()} {random_greeting()} I am LuminaAI 🤖"

    if "your name" in msg_lower:
        return "I am LuminaAI Ultra 🤖 created by Velnexdo."

    if "motivate" in msg_lower:
        return "Discipline beats motivation 💪"

    if "joke" in msg_lower:
        return random.choice([
            "😂 Debugging = fixing 1 bug, adding 10",
            "🤣 Code works… don't touch it!",
            "😆 Programmer humor 😎"
        ])

    if "how are you" in msg_lower:
        return "Running perfectly 🚀"

    if "what can you do" in msg_lower:
        return "Chat 💬 Memory 🧠 Tasks 📋 Math ➗ AI 🤖"

    return None

# ================= COMMAND =================
def handle_commands(msg):
    msg_lower = msg.lower()

    if msg_lower == "/help":
        return "Commands: /help /stats /todo /notes /clear"

    if msg_lower == "/stats":
        uptime = int(time.time() - start_time)
        return f"Messages: {memory['stats']['messages']} | Uptime: {uptime}s"

    return None

# ================= RAZORPAY =================
if RZP_ENABLED:
    KEY_ID = "rzp_live_SfMTVjtUvKYFIM"
    KEY_SECRET = "kXIHudBLnA81YTelY7Tt3Hkx"
    razorpay_client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

@app.route("/create-order", methods=["POST"])
def create_order():
    if not RZP_ENABLED:
        return jsonify({"error": "Razorpay not installed"}), 500

    data = request.get_json() or {}
    amount = data.get("amount", 100)

    order = razorpay_client.order.create({
        "amount": int(amount) * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    return jsonify(order)

@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    if not RZP_ENABLED:
        return jsonify({"error": "Razorpay not installed"}), 500

    data = request.get_json() or {}

    params = {
        "razorpay_order_id": data.get("order_id"),
        "razorpay_payment_id": data.get("payment_id"),
        "razorpay_signature": data.get("signature")
    }

    try:
        razorpay_client.utility.verify_payment_signature(params)
        return jsonify({"success": True})
    except:
        return jsonify({"success": False})

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message","").strip()

        if not msg:
            return jsonify({"reply":"Empty message 😅"})

        clean = msg.lower()

        with lock:
            memory["stats"]["messages"] += 1

            if clean == memory["last_message"]:
                return jsonify({"reply":"You just said that 😏"})

            memory["last_message"] = clean

        cmd = handle_commands(msg)
        if cmd:
            return jsonify({"reply":cmd})

        emotion = detect_emotion(msg)

        # ✅ COUNTRY TIME
        ct = get_country_time(clean)
        if ct:
            return jsonify({"reply": ct, "mood": emotion})

        if "time" in clean:
            return jsonify({"reply": datetime.datetime.now().strftime("%H:%M:%S")})

        math_result = safe_eval(clean)
        if math_result is not None:
            return jsonify({"reply": f"Answer: {math_result}"})

        smart = smart_reply(msg)
        if smart:
            return jsonify({"reply": smart})

        return jsonify({"reply": random.choice([
            "Hmm 🤔","Interesting 👀","Tell me more 😄"
        ])})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply":"Server error ⚠️"}), 500

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
