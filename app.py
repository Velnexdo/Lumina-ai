from flask import Flask, request, jsonify, render_template
import random
import re
import time
import datetime

app = Flask(__name__)

# ================= MEMORY SYSTEM =================
memory = {
    "facts": {},
    "mood": "neutral",
    "mode": "normal"
}

todos = []
notes = []
goals = []

start_time = time.time()

# ================= EMOTION ENGINE =================
def detect_emotion(msg):
    msg = msg.lower()
    if any(w in msg for w in ["sad", "cry", "bad", "upset"]):
        return "sad"
    if any(w in msg for w in ["happy", "good", "awesome", "love"]):
        return "happy"
    if any(w in msg for w in ["angry", "mad", "hate"]):
        return "angry"
    return "neutral"

# ================= MATH ENGINE =================
def solve_math(msg):
    try:
        msg = msg.replace("x", "*")
        if re.fullmatch(r"[0-9+\-*/ ().]+", msg):
            return eval(msg)
    except:
        return None

# ================= HOME ROUTE =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= CHAT =================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    msg = data.get("message", "")
    clean = msg.lower().strip()

    emotion = detect_emotion(msg)
    memory["mood"] = emotion

    now = datetime.datetime.now()

    print("MSG:", msg)

    # ================= EMOTION RESPONSES =================
    if emotion == "sad":
        return jsonify({"reply": "Hey 😔 I feel you're sad… I'm here for you ❤️", "mood": emotion})

    if emotion == "happy":
        return jsonify({"reply": "That's awesome 😄🔥 keep going!", "mood": emotion})

    if emotion == "angry":
        return jsonify({"reply": "Take a breath 😌 I'm here to help.", "mood": emotion})

    # ================= NAME =================
    if "my name is" in clean:
        name = clean.split("my name is")[-1].strip().capitalize()
        memory["facts"]["name"] = name
        return jsonify({"reply": f"Nice to meet you {name} 👋", "mood": emotion})

    if "what is my name" in clean:
        return jsonify({"reply": memory["facts"].get("name", "unknown"), "mood": emotion})

    # ================= BASIC =================
    if clean in ["hi", "hello", "hey"]:
        return jsonify({"reply": "Hello 👋 How can I help you?", "mood": emotion})

    if "time" in clean:
        return jsonify({"reply": now.strftime("%H:%M:%S"), "mood": emotion})

    if "joke" in clean:
        return jsonify({"reply": random.choice([
            "😂 Why did the computer laugh? It saw a byte!",
            "🤣 My code works… I have no idea why!"
        ]), "mood": emotion})

    # ================= MATH =================
    result = solve_math(msg)
    if result is not None:
        return jsonify({"reply": f"🧮 {result}", "mood": emotion})

    # ================= STORY =================
    if "tell story" in clean:
        return jsonify({"reply": random.choice([
            "Once an AI learned emotions 🤖",
            "A hacker discovered a living code city 💻",
            "An AI started thinking like humans 😳"
        ]), "mood": emotion})

    # ================= CODE =================
    if "write code" in clean:
        return jsonify({"reply": "```python\nprint('Hello from LuminaAI')\n```", "mood": emotion})

    # ================= GAME =================
    if "make game" in clean:
        return jsonify({"reply": "🎮 Cyber zombie survival RPG idea with AI enemies!", "mood": emotion})

    # ================= MEMORY =================
    if "remember" in clean:
        memory["facts"][msg] = True
        return jsonify({"reply": "Got it 🧠 I will remember that.", "mood": emotion})

    if "what do you remember" in clean:
        return jsonify({"reply": str(list(memory["facts"].keys())), "mood": emotion})

    # ================= TODO =================
    if clean.startswith("todo "):
        todos.append(clean.replace("todo ", ""))
        return jsonify({"reply": "Task added ✅", "mood": emotion})

    if "show todo" in clean:
        return jsonify({"reply": "\n".join(todos) if todos else "No todos", "mood": emotion})

    # ================= NOTES =================
    if clean.startswith("note "):
        notes.append(clean.replace("note ", ""))
        return jsonify({"reply": "Note saved 📝", "mood": emotion})

    # ================= GOALS =================
    if clean.startswith("goal "):
        goals.append(clean.replace("goal ", ""))
        return jsonify({"reply": "Goal added 🎯", "mood": emotion})

    # ================= UPTIME =================
    if "uptime" in clean:
        uptime = round(time.time() - start_time, 2)
        return jsonify({"reply": f"Uptime: {uptime}s", "mood": emotion})

    # ================= DEFAULT =================
    return jsonify({"reply": random.choice([
        "Hmm 🤔 I didn't get that",
        "Try something else 👍",
        "Tell me more 😄"
    ]), "mood": emotion})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)