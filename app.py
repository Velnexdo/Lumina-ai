"""
LuminaAI Ultra — Flask backend
Existing chat, training responses, OpenRouter image generation, Hugging Face
image-to-image editing, JSON2Video, Fish Audio TTS, sharing, and status routes.

Configure secrets as environment variables on your hosting provider.
Never commit API tokens to a public repository.
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from huggingface_hub import InferenceClient
from datetime import datetime, timezone
from threading import Lock
import base64
import io
import json
import logging
import os
import random
import re
import requests
import uuid

# ============================================================
# APP / SECURITY
# ============================================================

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

APP_NAME = "LuminaAI Ultra"
DOMAIN = "https://asklumina.in"

ALLOWED_ORIGINS = [
    "https://asklumina.in",
    "https://www.asklumina.in",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("lumina")

# ============================================================
# ENVIRONMENT / MODELS
# ============================================================

CHAT_API_KEY = os.environ.get("CHAT_API_KEY", "").strip()
IMAGE_API_KEY = os.environ.get("IMAGE_API_KEY", "").strip() or CHAT_API_KEY

# Hugging Face I2I only. Cloudflare is intentionally not used.
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
HF_I2I_MODEL = os.environ.get("HF_I2I_MODEL", "").strip()

FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "").strip()
JSON2VIDEO_API_KEY = os.environ.get("JSON2VIDEO_API_KEY", "").strip()
JSON2VIDEO_BASE_URL = os.environ.get(
    "JSON2VIDEO_BASE_URL", "https://api.json2video.com/v2"
).rstrip("/")

CHAT_MODEL = os.environ.get("CHAT_MODEL", "poolside/laguna-xs-2.1:free").strip()
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "recraft/recraft-v4-pro").strip()
FISH_MODEL_ID = os.environ.get(
    "FISH_MODEL_ID", "933563129e564b19a115bedd57b7406a"
).strip()

MAX_MESSAGE_LENGTH = 12000
MAX_IMAGE_PROMPT_LENGTH = 2000
MAX_EDIT_IMAGE_BYTES = 4 * 1024 * 1024
MAX_TTS_LENGTH = 5000
MAX_SHARE_TEXT_LENGTH = 30000

session = requests.Session()
history_lock = Lock()
# Note: in-memory history is process-local, not persistent across restarts.
chat_history = {}

# ============================================================
# TRAINING DATA
# ============================================================

TRAINING_FILE = os.environ.get("TRAINING_FILE", "training_data.json")


def normalize_text(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) <= 20:
        compact = text.replace(" ", "")
        if len(compact) >= 2:
            text = compact
    return text


def load_training_data():
    try:
        with open(TRAINING_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
        logger.warning("Training data must be a JSON object.")
    except FileNotFoundError:
        logger.info("%s not found; continuing without training data.", TRAINING_FILE)
    except (json.JSONDecodeError, OSError):
        logger.exception("Could not load training data.")
    return {}


TRAINING_DATA = load_training_data()


def build_training_index(data):
    index = {}
    for key, responses in data.items():
        normalized = normalize_text(key)
        if not normalized:
            continue
        if isinstance(responses, list):
            values = [str(item).strip() for item in responses if str(item).strip()]
        elif isinstance(responses, str) and responses.strip():
            values = [responses.strip()]
        else:
            values = []
        if values:
            index[normalized] = values
    return index


TRAINING_INDEX = build_training_index(TRAINING_DATA)


def get_trained_response(message):
    responses = TRAINING_INDEX.get(normalize_text(message))
    return random.choice(responses) if responses else None


# ============================================================
# SYSTEM PROMPT / OPENROUTER CHAT
# ============================================================

SYSTEM_PROMPT = f"""
You are {APP_NAME}, a futuristic AI assistant created by Velnexdo.
Be friendly, accurate, useful, respectful, and natural.
Explain complicated things clearly. Keep simple answers concise.
Write clean, complete code when appropriate and preserve existing functionality.
Never pretend to know something you do not know. If uncertain, say so.
If asked who made you, say: "I'm {APP_NAME} ✨ — created by Velnexdo."
Always identify yourself as {APP_NAME}; do not claim to be another company's assistant.
""".strip()


def ask_ai(message, session_id="default"):
    trained = get_trained_response(message)
    if trained:
        return trained

    if not CHAT_API_KEY:
        return "Chat service is not configured yet. Please set CHAT_API_KEY on the server."

    with history_lock:
        prior = chat_history.get(session_id, [])[-10:].copy()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(prior)
    messages.append({
        "role": "user",
        "content": str(message)[:MAX_MESSAGE_LENGTH],
    })

    response = session.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {CHAT_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": DOMAIN,
            "X-Title": APP_NAME,
        },
        json={
            "model": CHAT_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
        },
        timeout=90,
    )
    if not response.ok:
        logger.error("OpenRouter chat failed (%s): %s", response.status_code, response.text[:1000])
        response.raise_for_status()

    result = response.json()
    reply = result["choices"][0]["message"]["content"]
    with history_lock:
        chat_history.setdefault(session_id, []).extend([
            {"role": "user", "content": str(message)[:MAX_MESSAGE_LENGTH]},
            {"role": "assistant", "content": reply},
        ])
        chat_history[session_id] = chat_history[session_id][-20:]
    return reply


# ============================================================
# OPENROUTER IMAGE GENERATION (TEXT-TO-IMAGE)
# ============================================================

def generate_image_openrouter(prompt):
    if not IMAGE_API_KEY:
        return {"success": False, "error": "Image generation is not configured."}

    response = session.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {IMAGE_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": DOMAIN,
            "X-Title": APP_NAME,
        },
        json={
            "model": IMAGE_MODEL,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": str(prompt)[:MAX_IMAGE_PROMPT_LENGTH],
                }],
            }],
        },
        timeout=120,
    )
    if not response.ok:
        logger.error("OpenRouter image request failed (%s): %s", response.status_code, response.text[:1000])
        return {"success": False, "error": "Image provider request failed."}

    payload = response.json()
    message = payload.get("choices", [{}])[0].get("message", {})
    # OpenRouter image-capable models may return image URLs in message.images.
    images = message.get("images") or []
    if images:
        first = images[0]
        url = first.get("image_url", {}).get("url") or first.get("url")
        if url:
            return {"success": True, "image": url}

    content = message.get("content")
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url")
                if url:
                    return {"success": True, "image": url}

    return {
        "success": False,
        "error": "The configured model did not return an image. Check that IMAGE_MODEL supports image output.",
    }


# ============================================================
# HUGGING FACE IMAGE-TO-IMAGE
# ============================================================

def process_huggingface_img2img(prompt, base64_image, strength=0.65):
    if not HF_TOKEN:
        return {"success": False, "error": "HF_TOKEN is not configured on the server."}
    if not HF_I2I_MODEL:
        return {
            "success": False,
            "error": "HF_I2I_MODEL is not configured. Set it to a model that supports image-to-image inference.",
        }
    if not isinstance(prompt, str) or not prompt.strip():
        return {"success": False, "error": "Please enter an editing prompt."}
    if not isinstance(base64_image, str) or not base64_image.strip():
        return {"success": False, "error": "Please provide an image to edit."}

    try:
        encoded = base64_image.split(",", 1)[1] if "," in base64_image else base64_image
        image_bytes = base64.b64decode(encoded, validate=True)
        if not image_bytes:
            return {"success": False, "error": "The uploaded image is empty."}
        if len(image_bytes) > MAX_EDIT_IMAGE_BYTES:
            return {"success": False, "error": "Image must be 4 MB or smaller."}

        with Image.open(io.BytesIO(image_bytes)) as original:
            original.verify()
        with Image.open(io.BytesIO(image_bytes)) as original:
            image = original.convert("RGB")
        image.thumbnail((1536, 1536))

        strength = max(0.0, min(float(strength), 1.0))
        client = InferenceClient(
            model=HF_I2I_MODEL,
            token=HF_TOKEN,
            timeout=120,
        )
        # This requires an actual image-to-image model supported by the selected
        # Hugging Face Inference Provider. Not every Hub model is hosted for inference.
        output_image = client.image_to_image(
            prompt=prompt.strip()[:MAX_IMAGE_PROMPT_LENGTH],
            image=image,
            strength=strength,
        )

        output = io.BytesIO()
        output_image.save(output, format="PNG")
        output_b64 = base64.b64encode(output.getvalue()).decode("ascii")
        return {"success": True, "image": f"data:image/png;base64,{output_b64}"}

    except (ValueError, UnidentifiedImageError):
        return {"success": False, "error": "Invalid image or strength value."}
    except Exception:
        logger.exception("Hugging Face image editing failed.")
        return {
            "success": False,
            "error": "Hugging Face image editing failed. Check model support, provider availability, token permissions, and server logs.",
        }


# ============================================================
# ROUTES — HOME / CHAT
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
def chat_route():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    session_id = str(data.get("session_id") or data.get("conversation_id") or "default")[:100]

    if not isinstance(message, str) or not message.strip():
        return jsonify({"success": False, "reply": "Type something 😄", "error": "Message is required."}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"success": False, "error": "Message is too long."}), 413

    try:
        reply = ask_ai(message.strip(), session_id)
        return jsonify({
            "success": True,
            "reply": reply,
            "response": reply,
            "mood": "happy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "suggestions": [
                "Explain simply",
                "Write Roblox script",
                "Help me code",
                "Fix my code",
                "Give examples",
            ],
        })
    except Exception:
        logger.exception("Chat route failed.")
        return jsonify({"success": False, "reply": "Sorry, I couldn't contact the AI service right now."}), 502


# ============================================================
# ROUTES — TEXT-TO-IMAGE
# ============================================================

@app.route("/image", methods=["POST"])
@app.route("/api/image", methods=["POST"])
@app.route("/generate-image", methods=["POST"])
def image_route():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "Please enter an image prompt."}), 400
    if len(prompt) > MAX_IMAGE_PROMPT_LENGTH:
        prompt = prompt[:MAX_IMAGE_PROMPT_LENGTH]

    result = generate_image_openrouter(prompt)
    return jsonify(result), (200 if result.get("success") else 502)


# ============================================================
# ROUTES — IMAGE-TO-IMAGE EDITING (CLOUDFLARE NOT USED)
# ============================================================

@app.route("/api/edit-image", methods=["POST"])
@app.route("/edit-image", methods=["POST"])
def image_editor_route():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    image_data = data.get("image", "")
    strength = data.get("strength", 0.65)

    if not isinstance(prompt, str):
        return jsonify({"success": False, "error": "Prompt must be text."}), 400
    if not isinstance(image_data, str) or not image_data.strip():
        return jsonify({"success": False, "error": "Please provide an image to edit."}), 400
    try:
        strength = float(strength)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Strength must be a number from 0 to 1."}), 400

    result = process_huggingface_img2img(prompt, image_data, strength)
    return jsonify(result), (200 if result.get("success") else 502)


# ============================================================
# ROUTES — FISH AUDIO TEXT-TO-SPEECH
# ============================================================

@app.route("/api/tts", methods=["POST"])
@app.route("/tts", methods=["POST"])
def tts_route():
    if not FISH_AUDIO_API_KEY:
        return jsonify({"success": False, "error": "Fish Audio is not configured."}), 503

    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"success": False, "error": "Text is required."}), 400
    text = text[:MAX_TTS_LENGTH]

    try:
        response = session.post(
            "https://api.fish.audio/v1/tts",
            headers={
                "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
                "Content-Type": "application/json",
                "model": FISH_MODEL_ID,
                "format": "mp3",
            },
            json={"text": text, "reference_id": FISH_MODEL_ID},
            timeout=120,
        )
        if not response.ok:
            logger.error("Fish Audio failed (%s): %s", response.status_code, response.text[:1000])
            return jsonify({"success": False, "error": "Fish Audio request failed."}), 502

        audio_b64 = base64.b64encode(response.content).decode("ascii")
        return jsonify({"success": True, "audio": f"data:audio/mpeg;base64,{audio_b64}"})
    except Exception:
        logger.exception("Fish Audio TTS failed.")
        return jsonify({"success": False, "error": "Text-to-speech failed."}), 502


# ============================================================
# ROUTES — JSON2VIDEO
# ============================================================

@app.route("/api/video", methods=["POST"])
@app.route("/video", methods=["POST"])
def video_route():
    if not JSON2VIDEO_API_KEY:
        return jsonify({"success": False, "error": "JSON2Video is not configured."}), 503

    data = request.get_json(silent=True) or {}
    # Pass through a caller-supplied JSON2Video project payload.
    project = data.get("project", data)
    if not isinstance(project, dict):
        return jsonify({"success": False, "error": "Video project must be a JSON object."}), 400

    try:
        response = session.post(
            f"{JSON2VIDEO_BASE_URL}/movies",
            headers={
                "x-api-key": JSON2VIDEO_API_KEY,
                "Content-Type": "application/json",
            },
            json=project,
            timeout=60,
        )
        try:
            result = response.json()
        except ValueError:
            result = {"message": response.text[:1000]}
        return jsonify({"success": response.ok, "result": result}), (200 if response.ok else 502)
    except Exception:
        logger.exception("JSON2Video request failed.")
        return jsonify({"success": False, "error": "Video generation request failed."}), 502


# ============================================================
# ROUTES — SHARING
# ============================================================

@app.route("/api/share", methods=["POST"])
@app.route("/share", methods=["POST"])
def share_route():
    data = request.get_json(silent=True) or {}
    content = data.get("text", data.get("content", ""))
    if not isinstance(content, str) or not content.strip():
        return jsonify({"success": False, "error": "Nothing to share."}), 400
    if len(content) > MAX_SHARE_TEXT_LENGTH:
        return jsonify({"success": False, "error": "Shared content is too long."}), 413

    share_id = uuid.uuid4().hex[:12]
    # This stores only in process memory; use a database for persistent/public share links.
    if not hasattr(app, "shared_items"):
        app.shared_items = {}
    app.shared_items[share_id] = {
        "text": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return jsonify({
        "success": True,
        "id": share_id,
        "url": f"{DOMAIN}/share/{share_id}",
    })


@app.route("/share/<share_id>", methods=["GET"])
def get_shared_route(share_id):
    item = getattr(app, "shared_items", {}).get(share_id)
    if not item:
        return jsonify({"success": False, "error": "Share not found. Shares are temporary in this server version."}), 404
    return jsonify({"success": True, **item})


# ============================================================
# ROUTES — HEALTH / CONFIG STATUS
# ============================================================

@app.route("/api/status", methods=["GET"])
@app.route("/health", methods=["GET"])
def status_route():
    return jsonify({
        "status": "online",
        "application": APP_NAME,
        "engine_nodes": {
            "openrouter_chat": bool(CHAT_API_KEY),
            "openrouter_image_generation": bool(IMAGE_API_KEY),
            "huggingface_image_to_image": bool(HF_TOKEN and HF_I2I_MODEL),
            "fish_audio_tts": bool(FISH_AUDIO_API_KEY),
            "json2video": bool(JSON2VIDEO_API_KEY),
            # Cloudflare intentionally omitted.
        },
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({"success": False, "error": "Upload too large. Maximum request size is 5 MB."}), 413


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"success": False, "error": "Requested route was not found."}), 404


@app.errorhandler(500)
def internal_error(_error):
    logger.exception("Unhandled server error.")
    return jsonify({"success": False, "error": "Internal server error."}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
