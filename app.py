from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import re
import time
import datetime
import ast
import operator

app = Flask(__name__)
CORS(app)

# ================= MEMORY SYSTEM =================
memory = {
    "facts": {},
    "mood": "neutral",
    "mode": "normal",
    "last_message": "",
    "chat_history": [],

    # ✅ ADDED (NOT REMOVED ANYTHING)
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
            if isinstance(n, ast.Num):
                return n.n
            elif isinstance(n, ast.BinOp):
                return operators[type(n.op)](eval_node(n.left), eval_node(n.right))
            else:
                raise Exception("Invalid Expression")

        return eval_node(node)
    except:
        return None

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

    # ✅ NEW COMMANDS (ADDED ONLY)
    if "your name" in msg:
        return "I am LuminaAI Ultra 🤖 created by Velnexdo."

    if "explain ai simply" in msg:
        return "AI is a smart computer system that can learn, think, and make decisions like humans."

    if "motivate me" in msg:
        return "You are capable of amazing things. Stay consistent, keep improving, and never give up."

    # 🔽 ORIGINAL (UNCHANGED)
    if "who are you" in msg:
        return "I'm LuminaAI 🤖 — your smart assistant, friend, and helper."

    if "how are you" in msg:
        return "I'm doing awesome 😄 what about you?"

    if "what can you do" in msg:
        return "I can chat, solve math, store memory, manage tasks, generate ideas, and more 😎"

    if "why" in msg:
        return "Everything happens due to reasons and causes 🤔 depends on context."

    if "how" in msg:
        return "Step-by-step ⚙️ I can explain if you want!"

    if "what is ai" in msg:
        return "AI is technology that simulates human intelligence 🤖"

    if "who made you" in msg:
        return "I was made by Velnexdo (Vishal)🔥"

    return None

# ================= RANDOM KNOWLEDGE =================
def random_knowledge():
    return random.choice([
        "💡 Brain uses less power than a light bulb!",
        "🌍 Earth supports life (for now 😳)",
        "⚡ Light > Sound speed",
        "🧠 Brain sometimes beats computers!"
    ])

# ================= HOME =================
@app.route("/")
def home():
    try:
        return render_template("index.html")
    except:
        return "index.html missing 😅"

# ================= CHAT =================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", "")

        if not msg:
            return jsonify({"reply": "Empty message 😅", "mood": "neutral"})

        clean = msg.lower().strip()

        # 🔐 LOCK SYSTEM (ADDED)
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

        # 📊 STATS
        memory["stats"]["messages"] += 1

        # 🔁 REPEAT DETECTION
        if msg == memory["last_message"]:
            return jsonify({"reply": "You just said that 😏", "mood": "neutral"})

        # LIMIT CHAT HISTORY
        memory["chat_history"].append(msg)
        if len(memory["chat_history"]) > 50:
            memory["chat_history"].pop(0)

        memory["last_message"] = msg

        emotion = detect_emotion(msg)
        memory["mood"] = emotion

        now = datetime.datetime.now()

        # ================= AUTO LEARN =================
        if " is " in clean:
            parts = clean.split(" is ")
            if len(parts) == 2:
                memory["learned"][parts[0].strip()] = parts[1].strip()

        if clean in memory["learned"]:
            return jsonify({"reply": memory["learned"][clean], "mood": emotion})

        # ================= SEARCH =================
        if clean.startswith("search "):
            q = clean.replace("search ", "")
            results = []
            results += [t for t in todos if q in t]
            results += [n for n in notes if q in n]
            results += [g for g in goals if q in g]
            return jsonify({"reply": "\n".join(results) or "Nothing found", "mood": emotion})

        # ================= REMINDER =================
        if clean.startswith("remind "):
            try:
                parts = clean.split(" in ")
                text = parts[0].replace("remind ", "")
                sec = int(parts[1])
                reminders.append((time.time()+sec, text))
                return jsonify({"reply": f"Reminder set in {sec}s ⏰", "mood": emotion})
            except:
                return jsonify({"reply": "Format: remind <text> in <sec>", "mood": emotion})

        for r in reminders:
            if time.time() >= r[0]:
                reminders.remove(r)
                return jsonify({"reply": f"⏰ Reminder: {r[1]}", "mood": "happy"})

        # ================= GAME =================
        if "start game" in clean:
            memory["game"] = random.randint(1,10)
            return jsonify({"reply": "Guess number 1-10 🎯", "mood": emotion})

        if clean.isdigit() and memory["game"]:
            if int(clean) == memory["game"]:
                memory["game"] = None
                return jsonify({"reply": "🎉 Correct!", "mood": "happy"})
            return jsonify({"reply": "Wrong 😏 try again", "mood": emotion})

        # ================= MODE SYSTEM =================
        if "mode fun" in clean:
            memory["mode"] = "fun"
            return jsonify({"reply": "😂 Fun mode activated!", "mood": emotion})

        if "mode serious" in clean:
            memory["mode"] = "serious"
            return jsonify({"reply": "🧠 Serious mode on.", "mood": emotion})

        if "mode hacker" in clean:
            memory["mode"] = "hacker"
            return jsonify({"reply": "😈 Hacker mode enabled...", "mood": emotion})

        # ================= SMART =================
        smart = smart_reply(msg)
        if smart:
            return jsonify({"reply": smart, "mood": emotion})

        # ================= NAME =================
        if "my name is" in clean:
            name = clean.split("my name is")[-1].strip().capitalize()
            memory["facts"]["name"] = name
            return jsonify({"reply": f"Nice to meet you {name} 👋", "mood": emotion})

        if "what is my name" in clean:
            return jsonify({"reply": memory["facts"].get("name", "I don't know 😅"), "mood": emotion})

        # ================= EXTRA FEATURES BACK =================
        if "quote" in clean:
            return jsonify({"reply": "🔥 Dream big, start small.", "mood": emotion})

        if "story" in clean:
            return jsonify({"reply": "Once an AI changed the world 🤖", "mood": emotion})

        if "code" in clean:
            return jsonify({"reply": "```python\nprint('LuminaAI Ultra 🚀')\n```", "mood": emotion})

        if "game idea" in clean:
            return jsonify({"reply": "Cyber survival open world 🎮", "mood": emotion})

        if "export data" in clean:
            return jsonify({"reply": str(memory), "mood": emotion})

        if "clear all" in clean:
            todos.clear(); notes.clear(); goals.clear()
            memory["facts"].clear()
            return jsonify({"reply": "Everything cleared 🧹", "mood": emotion})

        # ================= PASSWORD =================
        if "password" in clean:
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789!@#"
            pwd = "".join(random.choice(chars) for _ in range(10))
            return jsonify({"reply": f"🔐 {pwd}", "mood": emotion})

        # ================= WEATHER =================
        if "weather" in clean:
            return jsonify({"reply": "🌤️ It's sunny 😎", "mood": emotion})

        # ================= BASIC =================
        if clean in ["hi", "hello", "hey"]:
            return jsonify({"reply": "Hello 👋", "mood": emotion})

        if "time" in clean:
            return jsonify({"reply": now.strftime("%H:%M:%S"), "mood": emotion})

        if "date" in clean:
            return jsonify({"reply": now.strftime("%Y-%m-%d"), "mood": emotion})

        # ================= JOKE =================
        if "joke" in clean:
            return jsonify({"reply": random.choice([
                "😂 Debugging = fixing 1 bug, adding 10",
                "🤣 Code works… don't touch it!",
                "😆 Programmer humor 😎"
            ]), "mood": emotion})

        # ================= FACT =================
        if "fact" in clean:
            return jsonify({"reply": random_knowledge(), "mood": emotion})

        # ================= MATH =================
        result = safe_eval(msg.replace("x", "*"))
        if result is not None:
            return jsonify({"reply": f"🧮 {result}", "mood": emotion})

        # ================= TODO =================
        if clean.startswith("todo "):
            todos.append(clean.replace("todo ", ""))
            return jsonify({"reply": "Task added ✅", "mood": emotion})

        if "show todo" in clean:
            return jsonify({"reply": "\n".join(todos) or "No todos", "mood": emotion})

        if "clear todo" in clean:
            todos.clear()
            return jsonify({"reply": "Todos cleared 🧹", "mood": emotion})

        # ================= NOTES =================
        if clean.startswith("note "):
            notes.append(clean.replace("note ", ""))
            return jsonify({"reply": "Note saved 📝", "mood": emotion})

        if "show notes" in clean:
            return jsonify({"reply": "\n".join(notes) or "No notes", "mood": emotion})

        # ================= GOALS =================
        if clean.startswith("goal "):
            goals.append(clean.replace("goal ", ""))
            return jsonify({"reply": "Goal added 🎯", "mood": emotion})

        if "show goals" in clean:
            return jsonify({"reply": "\n".join(goals) or "No goals", "mood": emotion})

        # ================= UPTIME =================
        if "uptime" in clean:
            uptime = int(time.time() - start_time)
            return jsonify({"reply": f"Uptime: {uptime}s", "mood": emotion})

        # ================= CONTEXT =================
        if "what did i say" in clean:
            return jsonify({"reply": f"You said: {memory['last_message']}", "mood": emotion})

        # ================= STATS =================
        if "stats" in clean:
            return jsonify({"reply": f"Messages: {memory['stats']['messages']}", "mood": emotion})

        # ================= DEFAULT =================
        replies = [
            "Hmm interesting 🤔",
            "Tell me more 😏",
            "Sounds cool 😎",
            "Explain more 🔍",
            "I'm thinking... 🧠"
        ]

        if memory["mode"] == "fun":
            replies.append("😂 bruh that's funny")
        elif memory["mode"] == "hacker":
            replies.append("💻 accessing data... interesting")
        elif memory["mode"] == "serious":
            replies = ["Please elaborate.", "Provide more details."]

        return jsonify({
            "reply": random.choice(replies),
            "mood": emotion
        })

    except Exception as e:
        print("🔥 ERROR:", e)
        return jsonify({
            "reply": "Server error ⚠️",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
