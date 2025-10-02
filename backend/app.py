import os
import json
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from rag_pipeline import generate_response  # Import RAG pipeline function

# Load Environment Variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Error: GEMINI_API_KEY is missing in .env file!")

# Flask App Setup
app = Flask(__name__)
CORS(app)

CONVERSATION_HISTORY_FILE = "conversation_history.json"

# Gemini API Endpoint
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateText?key={API_KEY}"
# GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}"

def load_conversation_history():
    """load conversation history from json file"""
    if os.path.exists(CONVERSATION_HISTORY_FILE):
        with open(CONVERSATION_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# save conversation history in json file
def save_conversation_history(history):
    """save conversation history to json file"""
    with open(CONVERSATION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

@app.route("/api/gemini", methods=["POST"])
def gemini_chat():
    """ Handle user query, run RAG pipeline, and get AI response. """
    try:
        # Get User Input from Request
        data = request.get_json()
        user_input = data.get("input", "")

        if not user_input:
            return jsonify({"error": "Input text is required"}), 400
        
        conversation_history = load_conversation_history()

        history_prompt = "\n".join(conversation_history[-2:])  # Get last 2 turns of conversation history
        prompt = f"""
        You are a travel agent AI. Continue the conversation considering the context below:

        {history_prompt}

        User: {user_input}
        AI:"""

        # Run RAG Pipeline to get Contextual Response
        # ai_response = generate_response(user_input)
        ai_response = generate_response(prompt)

        conversation_history.append(f"User: {user_input}")
        conversation_history.append(f"AI: {ai_response}")

        # limit conversation history to 20
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        # Save Conversation History
        save_conversation_history(conversation_history)

        # Return AI-generated Response
        return jsonify({"query": user_input, "response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def parse_itinerary(response_text):
    """ Parse Gemini response into structured JSON format. """
    itinerary = []
    day_pattern = re.compile(r"Day (\d+):(.+?)(?=Day \d+:|$)", re.DOTALL)
    matches = day_pattern.findall(response_text)
    
    for day, places_text in matches:
        # Clean up and split places by lines or commas
        places = [place.strip() for place in re.split(r"[\n,]", places_text) if place.strip()]
        itinerary.append({
            "day": int(day),
            "places": places
        })
    
    return itinerary

@app.route("/api/gemini-taiwan", methods=["POST"])
def gemini_chat_taiwan():
    """ Handle user query, send to Gemini API, and return structured JSON response. """
    try:
        # Get User Input from Request
        data = request.get_json()
        user_input = data.get("input", "")

        if not user_input:
            return jsonify({"status": "error", "message": "Input text is required"}), 400
        
        # Prepare Request Payload for Gemini API
        payload = {
            "model": "Gemini-v1",
            "prompt": f"Create a detailed Taiwan travel itinerary for the following query:\n\n{user_input}\n\nFormat each day as 'Day X: place1, place2, place3...'.",
            "max_tokens": 500,
            "temperature": 0.7
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        # Send Request to Gemini API
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)

        # Check if Request was Successful
        if response.status_code == 200:
            api_response = response.json()
            gemini_text = api_response.get("choices", [{}])[0].get("text", "")

            # Parse Gemini Response into Structured JSON
            itinerary = parse_itinerary(gemini_text)
            number_of_days = len(itinerary)
            
            # Format Response in JSON Format
            return jsonify({
                "status": "success",
                "number_of_days": number_of_days,
                "itinerary": itinerary
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Gemini API request failed with status code {response.status_code}"
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    """ Health check endpoint. """
    return "AI Travel Planner Backend is running!"

# ---------- CANNED NASA KNOWLEDGE (NO EXTERNAL CALLS) ----------
def canned_nasa_answer(user_input: str) -> str:
    """Return canned NASA knowledge as Markdown based on simple keyword routing."""
    q = (user_input or "").strip().lower()

    # Artemis / Moon
    if any(k in q for k in ["artemis", "moon", "lunar", "orion", "sls"]):
        return (
            "### Artemis Program (Moon)\n"
            "- **Goal:** Return humans to the Moon, build a sustained lunar presence, and prepare for Mars.\n"
            "- **Key elements:** Space Launch System (SLS), Orion spacecraft, Gateway (lunar orbit station), Artemis Base Camp.\n"
            "- **Science:** In-situ resource utilization (e.g., **water ice**), geology, and technology demos.\n"
            "- **Why it matters:** Testing long-duration surface ops and logistics for future Mars missions."
        )

    # JWST / Hubble
    if any(k in q for k in ["jwst", "webb", "hubble", "infrared telescope"]):
        return (
            "### JWST vs Hubble\n"
            "- **Webb (JWST):** Optimized for **infrared**; sees through dust, studies early galaxies, exoplanet atmospheres.\n"
            "- **Hubble:** Primarily **optical/UV** with some near-IR; iconic deep fields, nebulae, and galaxy morphology.\n"
            "- **Together:** Complementary views—Hubble's sharp optical imaging + Webb's deep IR sensitivity."
        )

    # ISS / passes
    if any(k in q for k in ["iss", "space station", "overhead", "pass"]):
        return (
            "### International Space Station (ISS)\n"
            "- **What:** A microgravity lab in low Earth orbit, continuously inhabited since 2000.\n"
            "- **Research:** Human physiology, materials science, fluid physics, Earth observation.\n"
            "- **Spotting:** Look for bright, fast passes shortly after sunset/before sunrise.\n"
            "- **Tip:** Many apps/site工具可依你位置顯示下一次可見時間。"
        )

    # APOD / images
    if any(k in q for k in ["apod", "astronomy picture", "nasa images", "壁紙", "桌布"]):
        return (
            "### NASA 影像資源\n"
            "- **APOD (Astronomy Picture of the Day):** 每日一張天文圖＋解說（Markdown 友善）。\n"
            "- **NASA Image Library:** 可搜尋任務、天體、太空人等主題影像。\n"
            "- **使用建議:** 圖片多為高解析，適合做桌布或簡報背景（遵循授權標示）。"
        )

    # Mars rovers
    if any(k in q for k in ["perseverance", "curiosity", "ingenuity", "mars rover", "火星車"]):
        return (
            "### 火星任務（Rovers/Helicopter）\n"
            "- **Perseverance:** 在 Jezero 隕石坑蒐集樣本，為未來樣本返回做準備。\n"
            "- **Curiosity:** 探測蓋爾隕石坑沉積岩與古代可居住環境跡象。\n"
            "- **Ingenuity:** 首架在他星飛行的直升機，技術示範意義重大。"
        )

    # Exoplanets / black holes / astro basics
    if any(k in q for k in ["exoplanet", "系外行星", "black hole", "黑洞", "supernova", "超新星"]):
        return (
            "### 天文基礎（系外行星與黑洞）\n"
            "- **系外行星偵測:** 凌日法（亮度下降）與徑向速度法（恆星抖動）。\n"
            "- **黑洞觀測:** 吸積盤 X-ray、恆星運動、重力波（LIGO/Virgo/KAGRA）。\n"
            "- **太空望遠鏡角色:** Webb/Hubble/凌日任務（如 TESS）相輔相成。"
        )

    # NASA Centers / visits
    if any(k in q for k in ["kennedy", "jpl", "johnson", "nasa center", "參觀", "visitor"]):
        return (
            "### NASA 參觀重點\n"
            "- **Kennedy Space Center (FL):** 發射史、土星五號、可能有現場/近距離發射活動。\n"
            "- **Johnson Space Center (TX):** 任務控制中心歷史與太空人訓練展示。\n"
            "- **JPL (CA):** 以深空機器人探測著稱（一般年度開放日需提前登記）。"
        )

    # Careers / internships
    if any(k in q for k in ["intern", "實習", "career", "工作", "nasa path"]):
        return (
            "### 在 NASA 發展\n"
            "- **Internships/Pathways:** 面向 STEM 領域學生的實習與轉正管道。\n"
            "- **常見背景:** 航太、機械、電機、資工、資料科學、地球科學等。\n"
            "- **作品集建議:** 展示系統整合、模擬分析、資料管線或影像處理專案。"
        )

    # Launches / rockets
    if any(k in q for k in ["launch", "發射", "rocket", "sls", "falcon", "atlas", "vulcan"]):
        return (
            "### 火箭與發射基礎\n"
            "- **軌道需求:** 達成軌道需要垂直上升＋重力轉彎進入水平高超音速。\n"
            "- **多級火箭:** 逐級丟棄空重，提升最終速度與酬載效率。\n"
            "- **任務類型:** LEO、GTO、深空探測（軌道設計與發射窗影響甚大）。"
        )

    # Default fallback
    return (
        "### NASA 快速總覽\n"
        "- **人類深空探索：** Artemis 計畫重返月球並為火星做準備。\n"
        "- **太空望遠鏡：** Hubble（光/UV）與 JWST（紅外）相互補強。\n"
        "- **近地任務：** ISS 微重力研究、地球觀測衛星（氣候、災害監測）。\n"
        "- **機器人探測：** 火星車、外太陽系探測器（木星/土星系）。\n"
        "- 想更精確？告訴我你想知道的**任務/主題關鍵字**（如 *Artemis、JWST、ISS、Mars*）。"
    )


@app.route("/api/nasa", methods=["POST"])
def nasa_canned():
    """
    Simple canned NASA knowledge endpoint.
    Request body: { "input": "<user text>" }
    Response: { "query": "<user text>", "response": "<markdown string>" }
    """
    try:
        data = request.get_json(force=True) or {}
        user_input = data.get("input", "")

        if not user_input:
            return jsonify({"error": "Input text is required"}), 400

        # Get canned markdown answer
        answer = canned_nasa_answer(user_input)

        # (Optional) keep a tiny log with your existing file
        history = load_conversation_history()
        history.append(f"User (NASA): {user_input}")
        history.append(f"AI (NASA): {answer}")
        save_conversation_history(history[-20:])  # keep last 20 lines

        return jsonify({"query": user_input, "response": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------- END: CANNED NASA ----------



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)