from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ==================================================
# CONFIG
# ==================================================

APP_NAME = "Lumina AI"

# 🔑 ENV KEYS
CHAT_API_KEY = os.environ.get("OPENROUTER_CHAT_API_KEY")
IMAGE_API_KEY = os.environ.get("OPENROUTER_IMAGE_API_KEY")

# fallback
if not IMAGE_API_KEY:
    IMAGE_API_KEY = CHAT_API_KEY

# ==================================================
# MODELS
# ==================================================

# 💬 CHAT MODEL
CHAT_MODEL = "inclusionai/ring-2.6-1t:free"

# 🎨 IMAGE MODEL
IMAGE_MODEL = "recraft/recraft-v4-pro"

# ==================================================
# SESSION
# ==================================================

session = requests.Session()

# ==================================================
# CHAT FUNCTION
# ==================================================

def ask_ai(message):

    if not CHAT_API_KEY:
        return "⚠️ OPENROUTER_CHAT_API_KEY missing"

    try:

        response = session.post(
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

                    {
                        "role": "system",
                        "content": f"""
You are {APP_NAME}, a modern AI assistant.

Rules:
- Be smart and helpful
- Keep answers clean
- Give coding help properly
- Be friendly
- Short answers for small questions
"""
                    },

                    {
                        "role": "user",
                        "content": message
                    }

                ],

                "temperature": 0.8,
                "max_tokens": 700

            },

            timeout=40
        )

        print("CHAT STATUS:", response.status_code)
        print("CHAT RAW:", response.text)

        data = response.json()

        # SUCCESS
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]

        # API ERROR
        if "error" in data:
            return f"⚠️ {data['error'].get('message', 'Unknown API error')}"

        return f"⚠️ Invalid response: {data}"

    except Exception as e:
        return f"⚠️ Chat Error: {str(e)}"


# ==================================================
# IMAGE FUNCTION
# ==================================================

def generate_image(prompt):

    if not IMAGE_API_KEY:
        return None

    try:

        response = session.post(
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

        print("IMAGE STATUS:", response.status_code)
        print("IMAGE RAW:", response.text)

        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            return data["data"][0].get("url")

        return None

    except Exception as e:
        print("IMAGE ERROR:", e)
        return None


# ==================================================
# ROUTES
# ==================================================

@app.route("/")
def home():
    return render_template("index.html")


# ==================================================
# CHAT ROUTE
# ==================================================

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json(force=True)

    msg = data.get("message", "").strip()

    if not msg:
        return jsonify({
            "reply": "Kuch likho 😄"
        })

    reply = ask_ai(msg)

    return jsonify({
        "reply": reply
    })


# ==================================================
# IMAGE ROUTE
# ==================================================

@app.route("/image", methods=["POST"])
def image():

    data = request.get_json(force=True)

    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({
            "error": "Prompt missing"
        }), 400

    image_url = generate_image(prompt)

    if not image_url:
        return jsonify({
            "error": "Image generation failed"
        }), 500

    return jsonify({
        "image": image_url
    })


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
