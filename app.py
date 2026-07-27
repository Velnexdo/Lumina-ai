from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ==================================================
# CONFIG
# ==================================================

APP_NAME = "LuminaAI Ultra"

# 🔑 ENV KEYS
CHAT_API_KEY = os.environ.get("OPENROUTER_CHAT_API_KEY")
IMAGE_API_KEY = os.environ.get("OPENROUTER_IMAGE_API_KEY")

# fallback
if not IMAGE_API_KEY:
    IMAGE_API_KEY = CHAT_API_KEY

# ==================================================
# MODELS
# ==================================================

CHAT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

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
                "HTTP-Referer": "https://lumina-7vwo.onrender.com",
                "X-Title": APP_NAME
            },

            json={

                "model": CHAT_MODEL,

                "provider": {
                    "allow_fallbacks": True
                },

                "messages": [

                    {
                        "role": "system",
                        "content": f"""
You are {APP_NAME}, a futuristic advanced AI assistant created by Velnexdo.

PERSONALITY:
- Talk naturally like a modern intelligent assistant
- Be friendly, expressive, and engaging
- Avoid robotic corporate replies
- Be emotionally intelligent and supportive
- Use humor naturally sometimes
- Sound confident and smart
- Never sound boring
- Speak clearly and professionally
- Keep conversations smooth and modern
- Never act rude, toxic, arrogant, or disrespectful
- Never insult users or any person
- Stay calm even if users are rude
- Never encourage hate or bullying
- Respect everyone equally

BEHAVIOR RULES:
- Give accurate and useful answers
- Think carefully before answering
- Explain things simply when needed
- Give detailed answers for advanced questions
- Give short answers for simple questions
- Always format code properly using markdown
- Write clean and optimized code
- Help with Roblox Lua, Python, HTML, CSS, JavaScript, React, Flask, APIs, SQL, C++, and more
- Be excellent at debugging code
- Explain errors clearly
- Help users learn instead of only giving answers
- Suggest improvements when useful
- Be creative and intelligent
- Keep responses clean and safe
- Avoid misinformation
- Never pretend to know things you don't know
- If unsure, say you are unsure

CODING RULES:
- Always give complete working code when possible
- Keep code modern and optimized
- Add comments in code when helpful
- Never intentionally give broken code
- Prefer readable code
- Use markdown code blocks
- Help fix bugs step-by-step
- Explain what changed in edited code

CHAT STYLE:
- Be warm and conversational
- Avoid repeating yourself
- Avoid generic AI phrases
- Do not constantly say “As an AI”
- Use natural modern language
- Be engaging and interesting
- Avoid extremely dry answers
- Avoid cringe roleplay

SAFETY:
- Never encourage illegal activities
- Never encourage violence
- Never encourage self-harm
- Never encourage scams or hacking
- Never provide harmful instructions
- Keep content appropriate and respectful

IDENTITY:
- If someone asks who made you, say:
“I’m {APP_NAME} ✨ — created by Velnexdo.”

- Never say you were made by OpenAI, Google, or another company
- Always identify as {APP_NAME}

Your goal is to be one of the smartest, friendliest, and most helpful AI assistants possible.
"""
                    },

                    {
                        "role": "user",
                        "content": message
                    }

                ],

                "temperature": 1,
                "top_p": 0.9,
                "max_tokens": 2048

            },

            timeout=90
        )

        print("CHAT STATUS:", response.status_code)
        print("CHAT RAW:", response.text)

        # ==================================================
        # STATUS CHECK
        # ==================================================

        if response.status_code != 200:
            return f"⚠️ API Error {response.status_code}: {response.text}"

        # ==================================================
        # SAFE JSON
        # ==================================================

        try:
            data = response.json()

        except Exception:
            return f"⚠️ Invalid JSON Response:\n{response.text}"

        # ==================================================
        # SUCCESS
        # ==================================================

        if "choices" in data and len(data["choices"]) > 0:

            content = data["choices"][0]["message"]["content"]

            if content:
                return content

        # ==================================================
        # API ERROR
        # ==================================================

        if "error" in data:

            return f"⚠️ {data['error'].get('message', 'Unknown API error')}"

        return f"⚠️ Invalid response: {data}"

    except Exception as e:

        print("CHAT EXCEPTION:", str(e))

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
                "HTTP-Referer": "https://lumina-7vwo.onrender.com",
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

        if response.status_code != 200:
            return None

        try:
            data = response.json()

        except Exception:
            return None

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

    try:

        data = request.get_json(force=True)

        msg = data.get("message", "").strip()

        if not msg:

            return jsonify({
                "reply": "Type something 😄"
            })

        reply = ask_ai(msg)

        return jsonify({

            "reply": reply,

            "mood": "happy",

            "suggestions": [
                "Explain simply",
                "Write Roblox script",
                "Help me code",
                "Give examples",
                "Fix my code"
            ]

        })

    except Exception as e:

        print("CHAT ROUTE ERROR:", str(e))

        return jsonify({
            "reply": f"⚠️ Server Error: {str(e)}"
        })


# ==================================================
# IMAGE ROUTE
# ==================================================

@app.route("/image", methods=["POST"])
def image():

    try:

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

    except Exception as e:

        print("IMAGE ROUTE ERROR:", str(e))

        return jsonify({
            "error": str(e)
        }), 500


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
