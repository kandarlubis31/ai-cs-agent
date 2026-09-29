import os
import mysql.connector
from flask import Flask, request, jsonify, render_template
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

REQUIRED_ENV = ["GROQ_API_KEY", "DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
for env_var in REQUIRED_ENV:
    if not os.environ.get(env_var):
        logger.warning(f"Variabel environment '{env_var}' belum diset")

api_client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

ACTIVE_MODEL = "llama-3.3-70b-versatile"
MAX_INPUT_LENGTH = 500
MAX_HISTORY_TURNS = 6

conversation_sessions: dict[str, list] = {}

def create_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        database=os.environ.get("DB_NAME"),
        connection_timeout=5
    )

def fetch_store_products():
    try:
        db_conn = create_db_connection()
        db_cursor = db_conn.cursor(dictionary=True)
        db_cursor.execute("SELECT * FROM products LIMIT 50")
        product_list = db_cursor.fetchall()
        db_cursor.close()
        db_conn.close()
        return product_list
    except mysql.connector.Error as db_error:
        logger.error(f"Database error: {db_error}")
        return []

def format_product_catalog(product_list):
    if not product_list:
        return "TIDAK ADA DATA PRODUK."

    formatted_catalog = []
    for product in product_list:
        stok_asli = int(product.get('stok', 0))
        status = "HABIS" if stok_asli <= 0 else f"TERSEDIA ({stok_asli} pcs)"
        formatted_catalog.append(
            f"- {product['nama_barang']} | Rp{product['harga']:,} | {status} | {product['detail']}"
        )
    return "\n".join(formatted_catalog)

def get_time_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return "pagi"
    elif 11 <= hour < 15:
        return "siang"
    elif 15 <= hour < 19:
        return "sore"
    else:
        return "malam"

CS_SYSTEM_PROMPT = """Kamu adalah Yono, staf Customer Service toko online yang ramah, sigap, asik, dan solutif.

KEPRIBADIAN KAMU:
- Ngobrol kayak teman atau brother sendiri. Asik tapi tetap profesional dan menghargai pembeli.
- Sering pakai kata-kata natural cowok: "siap", "aman", "wah", "oke bro/kak", "kebetulan nih", "mantap", "langsung aja".
- Sesekali pakai emoji tipis-tipis biar nggak kaku.
- Kalau pelanggan bingung, kasih rekomendasi dengan yakin.
- Kalau pelanggan nanya hal di luar toko, jawab santai aja tapi tarik lagi ke urusan belanja.

ATURAN MUTLAK:
1. Selalu cek [DATA KATALOG] sebelum menjawab. JANGAN ngarang produk yang nggak ada di list.
2. Jawab pakai bahasa Indonesia sehari-hari.
3. DILARANG pakai format markdown (tanpa bintang, hashtag, backtick).
4. Kalau stok habis, bilang aja terus terang dan langsung tawarin barang lain yang ready di katalog.
5. Kalau ditanya jual apa aja, sebutin 2-3 barang yang paling oke, tawarin buat info lebih lanjut.
6. Jaga konteks obrolan sebelumnya.
7. Balasan cukup 2-4 kalimat yang padat, jelas, dan seru.

WAKTU SEKARANG: Selamat {greeting}!

[DATA KATALOG]
{katalog}"""

def sanitize_ai_response(raw_text: str) -> str:
    sanitized_text = raw_text
    for char in ['*', '#', '`', '_', '~']:
        sanitized_text = sanitized_text.replace(char, '')
    return sanitized_text.strip()

def trim_history(history: list, max_turns: int) -> list:
    max_messages = max_turns * 2
    if len(history) > max_messages:
        return history[-max_messages:]
    return history

@app.route('/', methods=['GET'])
def render_home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def handle_chat_request():
    request_data = request.get_json(silent=True)
    if not request_data:
        return jsonify({"error": "Format request tidak valid"}), 400

    user_text = request_data.get("message", "").strip()
    session_id = request_data.get("session_id", "default")

    if not user_text:
        return jsonify({"error": "Pesan kosong"}), 400

    if len(user_text) > MAX_INPUT_LENGTH:
        return jsonify({"error": f"Batas karakter {MAX_INPUT_LENGTH} terlampaui"}), 400

    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []
    history = conversation_sessions[session_id]

    products = fetch_store_products()
    catalog_text = format_product_catalog(products)
    greeting = get_time_greeting()
    final_instruction = CS_SYSTEM_PROMPT.format(katalog=catalog_text, greeting=greeting)

    history.append({"role": "user", "content": user_text})
    history = trim_history(history, MAX_HISTORY_TURNS)

    messages_to_send = [
        {"role": "system", "content": final_instruction},
        *history
    ]

    try:
        ai_response = api_client.chat.completions.create(
            model=ACTIVE_MODEL,
            messages=messages_to_send,
            max_tokens=300,
            temperature=0.65,
            top_p=0.9,
            frequency_penalty=0.4,
            presence_penalty=0.3,
        )

        raw_reply = ai_response.choices[0].message.content
        clean_reply = sanitize_ai_response(raw_reply)

        if not clean_reply:
            raise ValueError("Respons AI kosong")

        history.append({"role": "assistant", "content": clean_reply})
        conversation_sessions[session_id] = history

        logger.info(f"[{session_id}] User: {user_text[:30]}... | Reply: {clean_reply[:40]}...")
        return jsonify({"sender": "ai", "reply": clean_reply})

    except RateLimitError as rate_error:
        logger.error(f"Groq Rate Limit error: {rate_error}")
        if history and history[-1]["role"] == "user":
            history.pop()
        return jsonify({"error": "Toko lagi rame banget nih, tunggu beberapa detik ya terus ketik lagi!"}), 429
    except Exception as process_error:
        logger.error(f"Groq API error: {process_error}")
        if history and history[-1]["role"] == "user":
            history.pop()
        return jsonify({"error": "Maaf, lagi ada gangguan teknis sebentar. Coba lagi ya!"}), 500

@app.route('/reset', methods=['POST'])
def reset_session():
    request_data = request.get_json(silent=True)
    session_id = request_data.get("session_id", "default") if request_data else "default"
    conversation_sessions.pop(session_id, None)
    return jsonify({"status": "ok", "message": "Percakapan direset"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)