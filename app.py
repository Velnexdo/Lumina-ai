from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os, requests, ast, operator

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ================= CONFIG =================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

AI_NAME = "LuminaAI"

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
                return operators[type(n.op)](
                    eval_node(n.left),
                    eval_node(n.right)
                )

        return eval_node(node)
    except:
        return None

# ================= AI CORE =================
def ask_ai(msg):

    if not OPENROUTER_API_KEY:
        return "⚠️ Missing API key in Render Environment Variables"

    for model in MODELS:
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://render.com",
                    "X-Title": AI_NAME
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""
You are Lumina AI, a friendly AI assistant and a helpful AI friend.

Personality:
- You are like a smart best friend
- You talk in simple, natural human language
- You are helpful, fun, and supportive
- You know your name is {AI_NAME} and you can say it naturally in conversation
- You NEVER say you're just a model unless asked
- You behave like a real chat companion

Always respond naturally like a friend talking.
"""
                        },
                        {"role": "user", "content": msg}
                    ],
                    "max_tokens": 700,
                    "temperature": 0.8
                },
                timeout=20
            )

            if res.status_code != 200:
                continue

            data = res.json()

            if data.get("choices"):
                return data["choices"][0]["message"]["content"]

        except:
            continue

    return "⚠️ AI temporarily unavailable"

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        msg = (request.json or {}).get("message", "").strip()

        if not msg:
            return jsonify({"reply": "Hey 😄 kya soch rahe ho?"})

        # simple math support
        math = safe_eval(msg)
        if math is not None:
            return jsonify({"reply": f"Answer: {math}"})

        # AI response
        reply = ask_ai(msg)

        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "Server error ⚠️"}), 500

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
