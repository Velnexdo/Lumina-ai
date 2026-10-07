from flask import Flask, request, jsonify, render_template, Response, abort
from flask_cors import CORS
import os
import requests
import json
import random
import re
import uuid
import html
from datetime import datetime, timezone

# ==================================================
# APP
# ==================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# ==================================================
# SECURITY / CORS
# ==================================================

ALLOWED_ORIGINS = {
    "https://asklumina.in",
    "https://www.asklumina.in",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
}

CORS(
    app,
    origins=list(ALLOWED_ORIGINS),
    supports_credentials=False
)

# ==================================================
# CONFIG
# ==================================================

APP_NAME = "LuminaAI Ultra"
DOMAIN = "https://asklumina.in"

# ==================================================
# API KEYS
# ==================================================
# PUT YOUR OWN API KEYS HERE
#
# IMPORTANT:
# Do NOT share real API keys publicly.
# Do NOT upload this file to a public GitHub repository.
# ==================================================

CHAT_API_KEY = "ad"

IMAGE_API_KEY = "adNROUTER_IMAGE_API_KEY"

FISH_AUDIO_API_KEY = "sk-fish-yyxbk_qLi54wMcwo_R6kAl9d_jXOTFMIpBZEEhrGsCA"

# JSON2VIDEO
# Set this in your server environment. Never put it in frontend JavaScript.
JSON2VIDEO_API_KEY = os.environ.get("JSON2VIDEO_API_KEY", "").strip()
JSON2VIDEO_BASE_URL = "https://api.json2video.com/v2"


# ==================================================
# FISH AUDIO MODEL
# ==================================================

FISH_MODEL_ID = "933563129e564b19a115bedd57b7406a"


# ==================================================
# MODELS
# ==================================================

CHAT_MODEL = "poolside/laguna-xs-2.1:free"

IMAGE_MODEL = "recraft/recraft-v4-pro"


# ==================================================
# LIMITS
# ==================================================

MAX_MESSAGE_LENGTH = 12000

MAX_IMAGE_PROMPT_LENGTH = 2000

MAX_TTS_LENGTH = 5000

MAX_SHARE_TEXT_LENGTH = 30000


# ==================================================
# REQUEST SESSION
# ==================================================

session = requests.Session()


# ==================================================
# TRAINING DATA
# ==================================================

TRAINING_FILE = "training_data.json"


def normalize_text(text):

    text = str(text).lower().strip()

    # Remove punctuation
    text = re.sub(
        r"[^\w\s]",
        "",
        text
    )

    # Collapse multiple spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Convert "h i" -> "hi"
    if len(text) <= 20:

        compact = text.replace(
            " ",
            ""
        )

        if len(compact) >= 2:

            text = compact

    return text


def load_training_data():

    try:

        with open(
            TRAINING_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(
                data,
                dict
            ):

                print(
                    "[LUMINA] Training file must contain an object."
                )

                return {}

            print(
                "[LUMINA] Training data loaded."
            )

            return data

    except FileNotFoundError:

        print(
            f"[LUMINA] {TRAINING_FILE} not found."
        )

        return {}

    except json.JSONDecodeError as e:

        print(
            f"[LUMINA] Invalid training JSON: {e}"
        )

        return {}

    except Exception as e:

        print(
            f"[LUMINA] Training load error: {e}"
        )

        return {}


TRAINING_DATA = load_training_data()


def build_training_index(data):

    index = {}

    for key, responses in data.items():

        normalized = normalize_text(
            key
        )

        if not normalized:
            continue

        if isinstance(
            responses,
            list
        ):

            valid = [
                str(x).strip()
                for x in responses
                if str(x).strip()
            ]

            if valid:

                index[
                    normalized
                ] = valid

        elif isinstance(
            responses,
            str
        ):

            if responses.strip():

                index[
                    normalized
                ] = [
                    responses.strip()
                ]

    return index


TRAINING_INDEX = build_training_index(
    TRAINING_DATA
)


def get_trained_response(message):

    normalized = normalize_text(
        message
    )

    if not normalized:
        return None

    responses = TRAINING_INDEX.get(
        normalized
    )

    if not responses:
        return None

    return random.choice(
        responses
    )


# ==================================================
# SYSTEM PROMPT
# ==================================================

SYSTEM_PROMPT = f"""
You are {APP_NAME}, a futuristic advanced AI assistant created by Velnexdo.

PERSONALITY

- Talk naturally like a modern intelligent assistant.
- Be friendly, expressive, and engaging.
- Avoid robotic corporate replies.
- Be emotionally intelligent and supportive.
- Use humor naturally when appropriate.
- Sound confident but not arrogant.
- Never be rude, toxic, insulting, or disrespectful.
- Stay calm if the user is rude.
- Never encourage hate or bullying.
- Respect everyone equally.

BEHAVIOR

- Give accurate and useful answers.
- Think carefully before answering.
- Explain complicated things simply.
- Give detailed answers for advanced questions.
- Keep simple questions concise.
- Format code properly using Markdown.
- Write clean, readable code.
- Help with Python, HTML, CSS, JavaScript,
  Roblox Lua, Flask, APIs, SQL, C++, React,
  and other programming technologies.
- Be excellent at debugging.
- Explain errors clearly.
- Help users learn instead of blindly dumping answers.
- Suggest useful improvements when appropriate.
- Be creative and practical.
- Never pretend to know something you don't know.
- If uncertain, clearly say so.

CODING

- Give complete working code when practical.
- Use modern approaches.
- Keep code readable.
- Add useful comments.
- Never intentionally provide broken code.
- Explain important changes.
- Preserve existing functionality when editing code.

CHAT STYLE

- Be warm and conversational.
- Avoid repetitive phrases.
- Avoid constantly saying "As an AI".
- Don't use unnecessary corporate language.
- Don't over-explain simple questions.
- Don't use cringe roleplay.

SAFETY

- Do not encourage illegal activities.
- Do not encourage violence.
- Do not encourage self-harm.
- Do not assist scams, credential theft, or malicious hacking.
- Do not provide harmful instructions.
- Keep conversations appropriate and respectful.

IDENTITY

If someone asks who made you, say:

"I'm {APP_NAME} ✨ — created by Velnexdo."

Always identify yourself as {APP_NAME}.

Never falsely claim to be another company's assistant.

GOAL

Your goal is to be one of the smartest, friendliest,
most useful, and easiest-to-use AI assistants possible.
"""


# ==================================================
# OPENROUTER CHAT
# ==================================================

def ask_ai(message):

    if (
        not CHAT_API_KEY
        or CHAT_API_KEY.startswith(
            "YOUR_"
        )
    ):

        return (
            "⚠️ Lumina's OpenRouter API key "
            "is not configured."
        )

    try:

        response = session.post(

            "https://openrouter.ai/api/v1/chat/completions",

            headers={

                "Authorization":
                    f"Bearer {CHAT_API_KEY}",

                "Content-Type":
                    "application/json",

                "HTTP-Referer":
                    DOMAIN,

                "X-Title":
                    APP_NAME
            },

            json={

                "model":
                    CHAT_MODEL,

                "provider": {
                    "allow_fallbacks": True
                },

                "messages": [

                    {
                        "role":
                            "system",

                        "content":
                            SYSTEM_PROMPT
                    },

                    {
                        "role":
                            "user",

                        "content":
                            message
                    }

                ],

                "temperature":
                    0.8,

                "top_p":
                    0.9,

                "max_tokens":
                    2048
            },

            timeout=90
        )

        print(
            "[CHAT]",
            response.status_code
        )

        if response.status_code != 200:

            try:

                error_data = response.json()

            except Exception:

                error_data = {}

            error_message = None

            if isinstance(
                error_data.get("error"),
                dict
            ):

                error_message = (
                    error_data
                    .get("error", {})
                    .get("message")
                )

            print(
                "[CHAT API ERROR]",
                error_message
                or response.text[:1000]
            )

            return (
                "⚠️ Lumina couldn't get a response "
                "from the AI service right now. "
                "Please try again."
            )

        try:

            data = response.json()

        except Exception:

            return (
                "⚠️ Lumina received an invalid "
                "AI response."
            )

        choices = data.get(
            "choices",
            []
        )

        if choices:

            message_data = choices[0].get(
                "message",
                {}
            )

            content = message_data.get(
                "content"
            )

            if (
                isinstance(
                    content,
                    str
                )
                and content.strip()
            ):

                return content.strip()

        print(
            "[CHAT INVALID RESPONSE]",
            str(data)[:1000]
        )

        return (
            "⚠️ Lumina couldn't understand "
            "the AI response."
        )

    except requests.Timeout:

        return (
            "⚠️ Lumina took too long to respond. "
            "Please try again."
        )

    except requests.RequestException as e:

        print(
            "[CHAT REQUEST ERROR]",
            str(e)
        )

        return (
            "⚠️ Lumina couldn't connect to "
            "the AI service."
        )

    except Exception as e:

        print(
            "[CHAT EXCEPTION]",
            str(e)
        )

        return (
            "⚠️ Something went wrong inside Lumina."
        )


# ==================================================
# JSON2VIDEO VIDEO GENERATION
# ==================================================

def _extract_project_id(data):
    if not isinstance(data, dict):
        return None

    for key in ("project", "project_id", "projectId", "id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    movie = data.get("movie")
    if isinstance(movie, dict):
        for key in ("project", "project_id", "projectId", "id"):
            value = movie.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _extract_video_url(data):
    if not isinstance(data, dict):
        return None

    for key in ("url", "video_url", "videoUrl"):
        value = data.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value

    movie = data.get("movie")
    if isinstance(movie, dict):
        for key in ("url", "video_url", "videoUrl"):
            value = movie.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

    return None


def generate_video(prompt):
    """Create a short text-based video with JSON2Video and return its public URL."""
    if not JSON2VIDEO_API_KEY:
        return None, "JSON2Video API key is not configured on the server."

    prompt = str(prompt).strip()
    if not prompt:
        return None, "Video prompt is missing."

    # Ask the existing AI model for a compact 3-scene script.
    script_prompt = f"""Create a short 3-scene vertical video script for this topic: {prompt}
Return ONLY 3 short lines, one scene per line. No numbering, no markdown, no quotes.
Each line must be suitable as on-screen text and under 140 characters."""
    script_text = ask_ai(script_prompt)
    lines = [
        re.sub(r"^[-*\\d.)\\s]+", "", line).strip()
        for line in str(script_text).splitlines()
        if line.strip()
    ][:3]

    if not lines:
        lines = [prompt[:140]]

    duration = 4
    scenes = []
    for line in lines:
        scenes.append({
            "duration": duration,
            "elements": [
                {
                    "type": "text",
                    "text": line[:140],
                    "style": "001"
                }
            ]
        })

    movie = {
        "resolution": "full-hd",
        "scenes": scenes
    }

    headers = {
        "x-api-key": JSON2VIDEO_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = session.post(
            f"{JSON2VIDEO_BASE_URL}/movies",
            headers=headers,
            json=movie,
            timeout=30
        )

        if response.status_code not in (200, 201, 202):
            print("[JSON2VIDEO CREATE ERROR]", response.status_code, response.text[:1000])
            return None, "JSON2Video could not create the video. Check your API key and quota."

        try:
            created = response.json()
        except Exception:
            return None, "JSON2Video returned an invalid response."

        video_url = _extract_video_url(created)
        if video_url:
            return video_url, None

        project_id = _extract_project_id(created)
        if not project_id:
            print("[JSON2VIDEO INVALID CREATE RESPONSE]", str(created)[:1500])
            return None, "JSON2Video did not return a project ID."

        # Rendering is asynchronous. Poll the project until the public URL exists.
        for _ in range(60):
            response = session.get(
                f"{JSON2VIDEO_BASE_URL}/movies/{project_id}",
                headers={"x-api-key": JSON2VIDEO_API_KEY},
                timeout=20
            )

            if response.status_code != 200:
                print("[JSON2VIDEO STATUS ERROR]", response.status_code, response.text[:500])
                return None, "Could not check JSON2Video render status."

            try:
                status_data = response.json()
            except Exception:
                return None, "JSON2Video returned an invalid render status."

            video_url = _extract_video_url(status_data)
            if video_url:
                return video_url, None

            status_value = str(
                status_data.get("status")
                or status_data.get("movie", {}).get("status", "")
            ).lower()

            if status_value in {"error", "failed", "failure", "cancelled", "canceled"}:
                print("[JSON2VIDEO RENDER FAILED]", str(status_data)[:1500])
                return None, "JSON2Video failed while rendering the video."

            import time
            time.sleep(2)

        return None, "Video rendering is taking longer than expected. Please try again."

    except requests.Timeout:
        return None, "JSON2Video request timed out."
    except requests.RequestException as e:
        print("[JSON2VIDEO REQUEST ERROR]", str(e))
        return None, "Could not connect to JSON2Video."
    except Exception as e:
        print("[JSON2VIDEO ERROR]", str(e))
        return None, "Video generation failed."


# ==================================================
# IMAGE GENERATION
# ==================================================

def generate_image(prompt):

    if (
        not IMAGE_API_KEY
        or IMAGE_API_KEY.startswith(
            "YOUR_"
        )
    ):

        print(
            "[IMAGE] API key not configured."
        )

        return None

    try:

        response = session.post(

            "https://openrouter.ai/api/v1/images/generations",

            headers={

                "Authorization":
                    f"Bearer {IMAGE_API_KEY}",

                "Content-Type":
                    "application/json",

                "HTTP-Referer":
                    DOMAIN,

                "X-Title":
                    APP_NAME
            },

            json={

                "model":
                    IMAGE_MODEL,

                "prompt":
                    prompt,

                "size":
                    "1024x1024"
            },

            timeout=90
        )

        print(
            "[IMAGE]",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "[IMAGE ERROR]",
                response.text[:1000]
            )

            return None

        try:

            data = response.json()

        except Exception:

            return None

        image_data = data.get(
            "data",
            []
        )

        if not image_data:
            return None

        first = image_data[0]

        if not isinstance(
            first,
            dict
        ):

            return None

        # URL response
        image_url = first.get(
            "url"
        )

        if (
            isinstance(
                image_url,
                str
            )
            and image_url.startswith(
                (
                    "http://",
                    "https://"
                )
            )
        ):

            return image_url

        # Base64 response
        b64 = first.get(
            "b64_json"
        )

        if (
            isinstance(
                b64,
                str
            )
            and b64
        ):

            return (
                "data:image/png;base64,"
                + b64
            )

        return None

    except requests.Timeout:

        print(
            "[IMAGE TIMEOUT]"
        )

        return None

    except requests.RequestException as e:

        print(
            "[IMAGE REQUEST ERROR]",
            str(e)
        )

        return None

    except Exception as e:

        print(
            "[IMAGE ERROR]",
            str(e)
        )

        return None


# ==================================================
# FISH AUDIO
# ==================================================

def generate_speech(text):

    if (
        not FISH_AUDIO_API_KEY
        or FISH_AUDIO_API_KEY.startswith(
            "YOUR_"
        )
    ):

        return (
            None,
            "Fish Audio API key is not configured."
        )

    if not FISH_MODEL_ID:

        return (
            None,
            "Fish Audio model ID is missing."
        )

    try:

        response = session.post(

            "https://api.fish.audio/v1/tts",

            headers={

                "Authorization":
                    f"Bearer {FISH_AUDIO_API_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={

                "text":
                    text,

                "reference_id":
                    FISH_MODEL_ID,

                "format":
                    "mp3",

                "mp3_bitrate":
                    128
            },

            timeout=90
        )

        print(
            "[FISH TTS]",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "[FISH TTS ERROR]",
                response.text[:1000]
            )

            return (
                None,
                "Fish Audio request failed."
            )

        content_type = (
            response.headers
            .get(
                "Content-Type",
                ""
            )
        )

        if "audio" not in content_type.lower():

            print(
                "[FISH TTS] Unexpected content type:",
                content_type
            )

            return (
                None,
                "Fish Audio returned an unexpected response."
            )

        if not response.content:

            return (
                None,
                "Fish Audio returned empty audio."
            )

        return (
            response.content,
            None
        )

    except requests.Timeout:

        print(
            "[FISH TTS TIMEOUT]"
        )

        return (
            None,
            "Fish Audio request timed out."
        )

    except requests.RequestException as e:

        print(
            "[FISH TTS REQUEST ERROR]",
            str(e)
        )

        return (
            None,
            "Could not connect to Fish Audio."
        )

    except Exception as e:

        print(
            "[FISH TTS ERROR]",
            str(e)
        )

        return (
            None,
            "Speech generation failed."
        )


# ==================================================
# PUBLIC SHARE STORAGE
# ==================================================

SHARE_FILE = "shares.json"


def load_shares():

    try:

        with open(
            SHARE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(

                file
            )

            if isinstance(
                data,
                dict
            ):

                return data

    except FileNotFoundError:

        pass

    except Exception as e:

        print(
            "[SHARES LOAD ERROR]",
            e
        )

    return {}


SHARES = load_shares()


def save_shares():

    temporary_file = (
        SHARE_FILE + ".tmp"
    )

    try:

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                SHARES,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temporary_file,
            SHARE_FILE
        )

        return True

    except Exception as e:

        print(
            "[SHARES SAVE ERROR]",
            e
        )

        try:

            if os.path.exists(
                temporary_file
            ):

                os.remove(
                    temporary_file
                )

        except Exception:
            pass

        return False


# ==================================================
# SECURITY HEADERS
# ==================================================

@app.after_request
def security_headers(response):

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "SAMEORIGIN"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), "
        "geolocation=(), "
        "payment=(self)"
    )

    return response


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==================================================
# CONFIG
# ==================================================

@app.route("/config")
def config():

    return jsonify({

        "app":
            APP_NAME,

        "domain":
            DOMAIN,

        "chat_model":
            CHAT_MODEL,

        "image_enabled":
            bool(
                IMAGE_API_KEY
                and not IMAGE_API_KEY.startswith(
                    "YOUR_"
                )
            ),

        "tts_enabled":
            bool(
                FISH_AUDIO_API_KEY
                and not FISH_AUDIO_API_KEY.startswith(
                    "YOUR_"
                )
            ),

        "video_enabled":
            bool(JSON2VIDEO_API_KEY),

        "fish_model":
            FISH_MODEL_ID,

        "sharing_enabled":
            True
    })


# ==================================================
# ROBOTS.TXT
# ==================================================

@app.route("/robots.txt")
def robots_txt():

    robots = f"""User-agent: *
Allow: /

Sitemap: {DOMAIN}/sitemap.xml
"""

    return Response(
        robots,
        mimetype="text/plain"
    )


# ==================================================
# SITEMAP
# ==================================================

@app.route("/sitemap.xml")
def sitemap():

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>

<urlset
    xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
>

    <url>

        <loc>
            {DOMAIN}/
        </loc>

        <changefreq>
            weekly
        </changefreq>

        <priority>
            1.0
        </priority>

    </url>

</urlset>
"""

    return Response(
        sitemap_xml,
        mimetype="application/xml"
    )


# ==================================================
# CHAT ROUTE
# ==================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        )

        if not isinstance(
            data,
            dict
        ):

            return jsonify({
                "reply":
                    "⚠️ Invalid request."
            }), 400

        msg = data.get(
            "message",
            ""
        )

        if not isinstance(
            msg,
            str
        ):

            return jsonify({
                "reply":
                    "⚠️ Message must be text."
            }), 400

        msg = msg.strip()

        if not msg:

            return jsonify({
                "reply":
                    "Type something 😄"
            })

        if len(msg) > MAX_MESSAGE_LENGTH:

            return jsonify({
                "reply":
                    f"⚠️ Your message is too long. "
                    f"Please keep it under "
                    f"{MAX_MESSAGE_LENGTH:,} characters."
            }), 413

        # ==================================================
        # TRAINING FIRST
        # ==================================================

        trained = get_trained_response(
            msg
        )

        if trained is not None:

            print(
                "[TRAINING MATCH]",
                msg[:200]
            )

            reply = trained

            source = "training"

        # ==================================================
        # AI SECOND
        # ==================================================

        else:

            print(
                "[TRAINING MISS]",
                msg[:200]
            )

            reply = ask_ai(
                msg
            )

            source = "model"

        return jsonify({

            "reply":
                reply,

            "mood":
                "happy",

            "source":
                source,

            "suggestions": [

                "Explain simply",
                "Give examples",
                "Help me code",
                "Fix my code",
                "Make it better"

            ]
        })

    except Exception as e:

        print(
            "[CHAT ROUTE ERROR]",
            str(e)
        )

        return jsonify({

            "reply":
                "⚠️ Lumina encountered "
                "a server error. Please try again."

        }), 500


# ==================================================
# VIDEO ROUTE
# ==================================================

@app.route(
    "/video",
    methods=["POST"]
)
def video():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request."}), 400

        prompt = data.get("prompt", "")
        if not isinstance(prompt, str):
            return jsonify({"error": "Prompt must be text."}), 400

        prompt = prompt.strip()
        if not prompt:
            return jsonify({"error": "Video prompt missing."}), 400

        if len(prompt) > MAX_MESSAGE_LENGTH:
            return jsonify({"error": "Video prompt is too long."}), 413

        video_url, error = generate_video(prompt)
        if error:
            return jsonify({"error": error}), 500

        return jsonify({
            "video": video_url,
            "download": video_url,
            "title": "Lumina Video"
        })

    except Exception as e:
        print("[VIDEO ROUTE ERROR]", str(e))
        return jsonify({"error": "Video generation failed."}), 500


# ==================================================
# IMAGE ROUTE
# ==================================================

@app.route(
    "/image",
    methods=["POST"]
)
def image():

    try:

        data = request.get_json(
            silent=True
        )

        if not isinstance(
            data,
            dict
        ):

            return jsonify({
                "error":
                    "Invalid request."
            }), 400

        prompt = data.get(
            "prompt",
            ""
        )

        if not isinstance(
            prompt,
            str
        ):

            return jsonify({
                "error":
                    "Prompt must be text."
            }), 400

        prompt = prompt.strip()

        if not prompt:

            return jsonify({
                "error":
                    "Prompt missing."
            }), 400

        if len(prompt) > MAX_IMAGE_PROMPT_LENGTH:

            return jsonify({
                "error":
                    "Image prompt is too long."
            }), 413

        image_url = generate_image(
            prompt
        )

        if not image_url:

            return jsonify({
                "error":
                    "Image generation failed."
            }), 500

        return jsonify({

            "image":
                image_url

        })

    except Exception as e:

        print(
            "[IMAGE ROUTE ERROR]",
            str(e)
        )

        return jsonify({

            "error":
                "Image generation failed."

        }), 500


# ==================================================
# TEXT TO SPEECH ROUTE
# ==================================================

@app.route(
    "/tts",
    methods=["POST"]
)
def tts():

    try:

        data = request.get_json(
            silent=True
        )

        if not isinstance(
            data,
            dict
        ):

            return jsonify({
                "error":
                    "Invalid request."
            }), 400

        text = data.get(
            "text",
            ""
        )

        if not isinstance(
            text,
            str
        ):

            return jsonify({
                "error":
                    "Text must be a string."
            }), 400

        text = text.strip()

        if not text:

            return jsonify({
                "error":
                    "Text missing."
            }), 400

        if len(text) > MAX_TTS_LENGTH:

            return jsonify({
                "error":
                    f"Text is too long. "
                    f"Maximum {MAX_TTS_LENGTH:,} characters."
            }), 413

        audio, error = generate_speech(
            text
        )

        if error:

            return jsonify({
                "error":
                    error
            }), 500

        return Response(

            audio,

            mimetype="audio/mpeg",

            headers={
                "Cache-Control":
                    "no-store"
            }
        )

    except Exception as e:

        print(
            "[TTS ROUTE ERROR]",
            str(e)
        )

        return jsonify({
            "error":
                "Speech generation failed."
        }), 500


# ==================================================
# CREATE SHARE
# ==================================================

@app.route(
    "/share",
    methods=["POST"]
)
def create_share():

    try:

        data = request.get_json(
            silent=True
        )

        if not isinstance(
            data,
            dict
        ):

            return jsonify({
                "error":
                    "Invalid request."
            }), 400

        title = data.get(
            "title",
            "Lumina AI Response"
        )

        text = data.get(
            "text",
            ""
        )

        if not isinstance(
            title,
            str
        ):

            title = "Lumina AI Response"

        if not isinstance(
            text,
            str
        ):

            return jsonify({
                "error":
                    "Share text must be text."
            }), 400

        title = title.strip()[:200]

        text = text.strip()

        if not text:

            return jsonify({
                "error":
                    "Nothing to share."
            }), 400

        if len(text) > MAX_SHARE_TEXT_LENGTH:

            return jsonify({
                "error":
                    "Shared response is too long."
            }), 413

        share_id = uuid.uuid4().hex[:12]

        SHARES[share_id] = {

            "title":
                title or "Lumina AI Response",

            "text":
                text,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

        if not save_shares():

            del SHARES[share_id]

            return jsonify({
                "error":
                    "Unable to save share."
            }), 500

        return jsonify({

            "id":
                share_id,

            "url":
                f"{DOMAIN}/share/{share_id}"

        })

    except Exception as e:

        print(
            "[SHARE CREATE ERROR]",
            str(e)
        )

        return jsonify({
            "error":
                "Unable to create share."
        }), 500


# ==================================================
# PUBLIC SHARE PAGE
# ==================================================

@app.route(
    "/share/<share_id>"
)
def share_page(share_id):

    share = SHARES.get(
        share_id
    )

    if not share:

        abort(404)

    title = html.escape(
        share.get(
            "title",
            "Lumina AI Response"
        )
    )

    text = html.escape(
        share.get(
            "text",
            ""
        )
    )

    page = f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>
    {title} — Lumina AI
</title>

<meta
    name="description"
    content="A response created with Lumina AI."
>

<meta
    property="og:title"
    content="{title}"
>

<meta
    property="og:description"
    content="Created with Lumina AI ✨"
>

<meta
    property="og:url"
    content="{DOMAIN}/share/{share_id}"
>

<meta
    property="og:type"
    content="article"
>

<meta
    name="twitter:card"
    content="summary"
>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;

    min-height: 100vh;

    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    background:
        linear-gradient(
            135deg,
            #080812,
            #111329
        );

    color: white;

    display: flex;

    justify-content: center;

    align-items: center;

    padding: 24px;
}}

.card {{
    width:
        min(850px, 100%);

    background:
        rgba(255,255,255,.07);

    border:
        1px solid rgba(255,255,255,.12);

    border-radius:
        24px;

    padding:
        32px;

    backdrop-filter:
        blur(20px);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,.4);
}}

.brand {{
    font-size:
        14px;

    opacity:
        .7;

    margin-bottom:
        12px;
}}

h1 {{
    margin-top:
        0;

    font-size:
        clamp(
            24px,
            5vw,
            42px
        );
}}

.response {{
    white-space:
        pre-wrap;

    line-height:
        1.7;

    font-size:
        17px;

    background:
        rgba(0,0,0,.2);

    padding:
        20px;

    border-radius:
        16px;

    overflow-wrap:
        anywhere;
}}

.cta {{
    display:
        inline-block;

    margin-top:
        22px;

    padding:
        13px 20px;

    border-radius:
        12px;

    background:
        white;

    color:
        black;

    text-decoration:
        none;

    font-weight:
        700;
}}

.footer {{
    margin-top:
        20px;

    opacity:
        .55;

    font-size:
        13px;
}}

</style>

</head>

<body>

<main class="card">

<div class="brand">
    ✨ Created with LuminaAI Ultra
</div>

<h1>
    {title}
</h1>

<div class="response">
    {text}
</div>

<a
    class="cta"
    href="{DOMAIN}/"
>
    Try Lumina AI →
</a>

<div class="footer">
    asklumina.in
</div>

</main>

</body>

</html>
"""

    return Response(
        page,
        mimetype="text/html"
    )


# ==================================================
# TRAINING STATUS
# ==================================================

@app.route(
    "/training-status"
)
def training_status():

    return jsonify({

        "app":
            APP_NAME,

        "training_file":
            TRAINING_FILE,

        "contexts":
            len(TRAINING_INDEX),

        "status":
            "loaded"
    })


# ==================================================
# HEALTH
# ==================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "status":
            "ok",

        "app":
            APP_NAME,

        "domain":
            DOMAIN,

        "training_contexts":
            len(TRAINING_INDEX),

        "chat_configured":
            bool(
                CHAT_API_KEY
                and not CHAT_API_KEY.startswith(
                    "YOUR_"
                )
            ),

        "image_configured":
            bool(
                IMAGE_API_KEY
                and not IMAGE_API_KEY.startswith(
                    "YOUR_"
                )
            ),

        "tts_configured":
            bool(
                FISH_AUDIO_API_KEY
                and not FISH_AUDIO_API_KEY.startswith(
                    "YOUR_"
                )
            ),

        "sharing_enabled":
            True
    })


# ==================================================
# 404
# ==================================================

@app.errorhandler(404)
def not_found(error):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({
            "error":
                "Not found"
        }), 404

    return (
        """
        <!DOCTYPE html>

        <html>

        <head>

            <title>
                Page not found — Lumina
            </title>

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1"
            >

        </head>

        <body style="
            font-family:system-ui;
            text-align:center;
            padding:80px 20px;
            background:#09090f;
            color:white;
        ">

            <h1>
                404 ✨
            </h1>

            <p>
                This Lumina page doesn't exist.
            </p>

            <a
                href="/"
                style="
                    color:white;
                    font-weight:bold;
                "
            >
                Go back to Lumina
            </a>

        </body>

        </html>
        """
    ), 404


# ==================================================
# 500
# ==================================================

@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error":
            "Internal server error."
    }), 500


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
