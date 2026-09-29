import os
import mysql.connector
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

REQUIRED_ENV = ["DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"]
for env_var in REQUIRED_ENV:
    if not os.environ.get(env_var):
        logger.warning(f"Variabel environment '{env_var}' belum diset")

api_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

ACTIVE_MODEL = "qwen2.5:1.5b"
MAX_INPUT_LENGTH = 500

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

CS_SYSTEM_PROMPT = """Kamu staf CS toko.
ATURAN:
1. Jawab HANYA berdasarkan [DATA KATALOG] di bawah ini.
2. Jawab langsung, singkat, santai, tanpa markdown.
3. Jika ditanya barang apa saja yang dijual, sebutkan langsung dari [DATA KATALOG].

[DATA KATALOG]
{katalog}"""

def sanitize_ai_response(raw_text: str) -> str:
    sanitized_text = raw_text
    for char in ['*', '#', '`', '_', '~']:
        sanitized_text = sanitized_text.replace(char, '')
    return sanitized_text.strip()

@app.route('/', methods=['GET'])
def render_home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def handle_chat_request():
    request_data = request.get_json(silent=True)
    if not request_data:
        return jsonify({"error": "Format request tidak valid"}), 400

    user_text = request_data.get("message", "").strip()
    if not user_text:
        return jsonify({"error": "Pesan kosong"}), 400

    if len(user_text) > MAX_INPUT_LENGTH:
        return jsonify({"error": f"Batas karakter {MAX_INPUT_LENGTH} terlampaui"}), 400

    products = fetch_store_products()
    catalog_text = format_product_catalog(products)
    final_instruction = CS_SYSTEM_PROMPT.format(katalog=catalog_text)

    try:
        ai_response = api_client.chat.completions.create(
            model=ACTIVE_MODEL,
            messages=[
                {"role": "system", "content": final_instruction},
                {"role": "user", "content": user_text}
            ],
            max_tokens=150,
            temperature=0.1,
        )

        clean_reply = sanitize_ai_response(ai_response.choices[0].message.content)
        
        if not clean_reply:
            raise ValueError("Respons AI kosong")

        logger.info(f"User: {user_text[:50]} | Reply: {clean_reply[:50]}")
        return jsonify({"sender": "ai", "reply": clean_reply})

    except Exception as process_error:
        logger.error(f"Ollama API error: {process_error}")
        return jsonify({"error": "Gagal menghubungi AI lokal"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)