from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import re
import time
import datetime
import ast
import operator
import os
import threading

app = Flask(__name__)
CORS(app)

lock = threading.Lock()

# ================= MEMORY SYSTEM =================
memory = {
    "facts": {},
    "mood": "neutral",
    "mode": "normal",
    "last_message": "",
    "chat_history": [],

    # ✅ ADDED
    "learned": {},
    "pin": None,
    "locked": False,
    "stats": {"messages": 0},
    "game": None
}

todos = []
notes = []
goals = []
reminders = []

start_time = time.time()

# ================= SAFE MATH ENGINE =================
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
            elif isinstance(n, ast.Num):
                return n.n
            elif isinstance(n, ast.BinOp):
                return operators[type(n.op)](eval_node(n.left), eval_node(n.right))
            else:
                raise Exception("Invalid Expression")

        return eval_node(node)
    except:
        return None

# ================= GREETINGS ENGINE (NEW) =================
def time_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning 🌅"
    elif 12 <= hour < 17:
        return "Good Afternoon ☀️"
    elif 17 <= hour < 21:
        return "Good Evening 🌇"
    else:
        return "Good Night 🌙"

def random_greeting():
    return random.choice([
        "Hey there 😄",
        "Hello buddy 👋",
        "Yo! What’s up 😎",
        "Hi hi 👋",
        "Aree welcome 😁",
        "Namaste 🙏 (AI style 😄)"
    ])

# ================= EMOTION ENGINE =================
def detect_emotion(msg):
    msg = msg.lower()
    if any(w in msg for w in ["sad", "cry", "bad", "upset", "depressed"]):
        return "sad"
    if any(w in msg for w in ["happy", "good", "awesome", "love", "great"]):
        return "happy"
    if any(w in msg for w in ["angry", "mad", "hate", "annoyed"]):
        return "angry"
    if any(w in msg for w in ["bored", "nothing to do"]):
        return "bored"
    return "neutral"

# ================= SMART AI =================
def smart_reply(msg):
    msg = msg.lower()

    # ===== GREETINGS (NEW) =====
    if any(w in msg for w in ["hi", "hello", "hey", "yo"]):
        return f"{time_greeting()} {random_greeting()} I am LuminaAI 🤖"

    if "good morning" in msg:
        return "Good Morning 🌅 Hope you have a great day!"

    if "good night" in msg:
        return "Good Night 🌙 Sleep well!"

    if "your name" in msg:
        return "I am LuminaAI Ultra 🤖 created by Velnexdo."

    if "explain ai simply" in msg:
        return "AI is a smart system that learns, thinks, and makes decisions like humans."

    if "motivate me" in msg:
        return "Stay consistent. Small progress daily = big success 🚀"

    if "joke" in msg:
        return random.choice([
            "😂 Debugging = fixing 1 bug, adding 10",
            "🤣 Code works… don't touch it!",
            "😆 Programmer humor 😎"
        ])

    if "who are you" in msg:
        return "I'm LuminaAI 🤖 — your smart assistant."

    if "how are you" in msg:
        return "I'm doing awesome 😄"

    if "what can you do" in msg:
        return "Chat, memory, tasks, math, ideas 😎"

    if "why" in msg:
        return "Depends on context 🤔"

    if "how" in msg:
        return "Step-by-step ⚙️"

    if "what is ai" in msg:
        return "AI = human-like intelligence in machines 🤖"

    if "who made you" in msg:
        return "Made by Velnexdo 🔥"

    return None

# ================= RANDOM KNOWLEDGE =================
def random_knowledge():
    return random.choice([
        "💡 Brain uses less power than a bulb!",
        "🌍 Earth supports life",
        "⚡ Light is faster than sound",
        "🧠 Brain beats computers sometimes"
    ])

# ================= HOME =================
@app.route("/")
def home():
    try:
        return render_template("index.html")
    except:
        return "LuminaAI running 🚀 (index.html missing)"

@app.route("/health")
def health():
    return "OK"

# ================= CHAT =================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        if not msg:
            return jsonify({"reply": "Empty message 😅", "mood": "neutral"})

        clean = msg.lower().strip()

        with lock:

            if memory["locked"]:
                if clean.startswith("unlock "):
                    pin = clean.split("unlock ")[-1]
                    if pin == memory["pin"]:
                        memory["locked"] = False
                        return jsonify({"reply": "🔓 Unlocked!", "mood": "happy"})
                    return jsonify({"reply": "Wrong PIN ❌", "mood": "angry"})
                return jsonify({"reply": "🔒 Locked system", "mood": "neutral"})

            if clean.startswith("set pin "):
                memory["pin"] = clean.split("set pin ")[-1]
                return jsonify({"reply": "PIN set 🔐", "mood": "happy"})

            if "lock system" in clean:
                memory["locked"] = True
                return jsonify({"reply": "System locked 🔒", "mood": "neutral"})

            memory["stats"]["messages"] += 1

            if msg == memory["last_message"]:
                return jsonify({"reply": "You just said that 😏", "mood": "neutral"})

            memory["chat_history"].append(msg)
            if len(memory["chat_history"]) > 50:
                memory["chat_history"].pop(0)

            memory["last_message"] = msg

        emotion = detect_emotion(msg)
        memory["mood"] = emotion

        now = datetime.datetime.now()

        if " is " in clean:
            parts = clean.split(" is ")
            if len(parts) == 2:
                memory["learned"][parts[0].strip()] = parts[1].strip()

        if clean in memory["learned"]:
            return jsonify({"reply": memory["learned"][clean], "mood": emotion})

        smart = smart_reply(msg)
        if smart:
            return jsonify({"reply": smart, "mood": emotion})

        if "time" in clean:
            return jsonify({"reply": now.strftime("%H:%M:%S"), "mood": emotion})

        if "date" in clean:
            return jsonify({"reply": now.strftime("%Y-%m-%d"), "mood": emotion})

        if "fact" in clean:
            return jsonify({"reply": random_knowledge(), "mood": emotion})

        return jsonify({
            "reply": random.choice([
                "Hmm interesting 🤔",
                "Tell me more 😏",
                "Sounds cool 😎"
            ]),
            "mood": emotion
        })

    except Exception as e:
        print("🔥 ERROR:", e)
        return jsonify({"reply": "Server error ⚠️"}), 500

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
