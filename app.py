from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time, ast, operator, threading, requests, os

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

lock = threading.Lock()

# ================= CONFIG =================
# ✅ Correct: env variable name use karo
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# 🔥 Multiple models (fallback)
MODELS = [
    "mistralai/mistral-7b-instruct",
    "meta-llama/llama-3-8b-instruct"
]

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

        return eval_node(node)
    except:
        return None

# ================= AI =================
def ask_ai(msg):
    if not OPENROUTER_API_KEY:
        return "⚠️ API key missing. Set OPENROUTER_API_KEY"

    for model in MODELS:
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "LuminaAI"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are LuminaAI, a smart, friendly, human-like assistant. Give clear and helpful answers."
                        },
                        {"role": "user", "content": msg}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.7
                },
                timeout=20
            )

            print("MODEL:", model, "STATUS:", res.status_code)

            if res.status_code != 200:
                print("ERROR:", res.text)
                continue

            data = res.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("AI ERROR:", e)
            continue

    return "⚠️ AI failed (check API key / quota)"

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json() or {}
        msg = data.get("message", "").strip()

        if not msg:
            return jsonify({"reply": "Say something 😄"})

        # Optional math
        math = safe_eval(msg)
        if math is not None:
            return jsonify({"reply": f"Answer: {math}"})

        # 🔥 PURE AI
        reply = ask_ai(msg)

        return jsonify({"reply": reply})

    except Exception as e:
        print("SERVER ERROR:", e)
        return jsonify({"reply": "Error ⚠️"}), 500

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
