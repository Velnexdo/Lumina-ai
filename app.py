from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os, requests

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ================= CONFIG =================

APP_NAME = "Lumina AI"

# 🔑 SEPARATE KEYS (Render ENV)
CHAT_API_KEY = os.environ.get("OPENROUTER_CHAT_API_KEY")
IMAGE_API_KEY = os.environ.get("OPENROUTER_IMAGE_API_KEY")

# fallback (agar image key na ho toh chat key use kare)
if not IMAGE_API_KEY:
    IMAGE_API_KEY = CHAT_API_KEY

# MODELS
CHAT_MODEL = "openai/gpt-chat-latest"
IMAGE_MODEL = "recraft/recraft-v4-pro"

session = requests.Session()


# ================= CHAT =================
def ask_ai(message):
    if not CHAT_API_KEY:
        return "⚠️ CHAT API KEY missing (OPENROUTER_CHAT_API_KEY)"

    try:
        res = session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CHAT_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://render.com",
                "X-Title": APP_NAME
            },
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": f"You are {APP_NAME}, a helpful AI assistant."},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,
                "max_tokens": 615
            },
            timeout=20
        )

        data = res.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        return f"⚠️ Chat error: {data}"

    except Exception as e:
        return f"⚠️ Error: {str(e)}"


# ================= IMAGE =================
def generate_image(prompt):
    if not IMAGE_API_KEY:
        return None

    try:
        res = session.post(
            "https://openrouter.ai/api/v1/images/generations",
            headers={
                "Authorization": f"Bearer {IMAGE_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://render.com",
                "X-Title": APP_NAME
            },
            json={
                "model": IMAGE_MODEL,
                "prompt": prompt,
                "size": "1024x1024"
            },
            timeout=60
        )

        data = res.json()

        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("url")

        return None

    except Exception as e:
        return str(e)


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("index.html")


# 💬 CHAT ROUTE
@app.route("/chat", methods=["POST"])
def chat():
    msg = (request.json or {}).get("message", "").strip()

    if not msg:
        return jsonify({"reply": "Kuch likho 😄"})

    reply = ask_ai(msg)
    return jsonify({"reply": reply})


# 🎨 IMAGE ROUTE
@app.route("/image", methods=["POST"])
def image():
    prompt = (request.json or {}).get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt missing"}), 400

    result = generate_image(prompt)

    if not result:
        return jsonify({"error": "Image generation failed"}), 500

    return jsonify({"image": result})


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
