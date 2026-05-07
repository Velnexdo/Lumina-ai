from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
import ast
import operator

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ================= CONFIG =================
XAI_API_KEY = os.environ.get("XAI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODEL = "grok-2-latest"  # ⚠️ agar 400 error aaye to "grok-2-latest" try karna

# ================= SAFE MATH =================
operators_map = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod
}

def safe_eval(expr):
    try:
        node = ast.parse(expr, mode='eval').body

        def eval_node(n):
            if isinstance(n, ast.Constant):
                return n.value

            elif isinstance(n, ast.BinOp):
                return operators_map[type(n.op)](
                    eval_node(n.left),
                    eval_node(n.right)
                )

            elif isinstance(n, ast.UnaryOp):
                return -eval_node(n.operand)

        return eval_node(node)

    except:
        return None

# ================= AI CHAT (GROK) =================
def ask_ai(msg):

    if not XAI_API_KEY:
        return "⚠️ Missing xAI API key"

    try:
        res = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are LuminaAI Ultra, a smart, fast, friendly AI assistant made by V_Velnexdo."
                    },
                    {
                        "role": "user",
                        "content": msg
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 800
            },
            timeout=40
        )

        if res.status_code != 200:
            print("xAI ERROR:", res.text)
            return f"⚠️ API Error: {res.status_code}"

        data = res.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI ERROR:", e)
        return "⚠️ AI unavailable"

# ================= IMAGE GENERATION (OPENROUTER) =================
def generate_image(prompt):

    if not OPENROUTER_API_KEY:
        return {"error": "Missing OpenRouter API key"}

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-image-1",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "modalities": ["image"]
            },
            timeout=60
        )

        if res.status_code != 200:
            print("IMAGE ERROR:", res.text)
            return {"error": res.text}

        data = res.json()

        image_url = data["choices"][0]["message"]["images"][0]["image_url"]

        return {"image": image_url}

    except Exception as e:
        print("IMAGE ERROR:", e)
        return {"error": str(e)}

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= CHAT =================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        msg = data.get("message", "").strip()

        if not msg:
            return jsonify({"reply": "Say something 😄"})

        # Math support
        math = safe_eval(msg)
        if math is not None:
            return jsonify({"reply": f"Answer: {math}"})

        reply = ask_ai(msg)

        return jsonify({
            "reply": reply,
            "mood": "smart",
            "suggestions": [
                "Explain AI",
                "Write code",
                "Make Roblox script",
                "Generate ideas"
            ]
        })

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"reply": "⚠️ Server error"}), 500

# ================= IMAGE =================
@app.route("/generate-image", methods=["POST"])
def image():
    try:
        data = request.json or {}
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return jsonify({"error": "Prompt required"})

        return jsonify(generate_image(prompt))

    except Exception as e:
        print("IMAGE ERROR:", e)
        return jsonify({"error": "Image failed"}), 500

# ================= HEALTH =================
@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "model": MODEL
    })

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
