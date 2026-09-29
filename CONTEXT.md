# ai_cs_agent — CONTEXT

## Apa ini
Customer service AI berbasis Flask (Python) dengan database MySQL. Chatbot CS yang
menjawab pertanyaan pelanggan via API LLM (OpenAI-compatible / Groq), dengan fallback
rate-limit handling. Ada varian `app_lokal.py` untuk menjalankan lokal tanpa konfigurasi penuh.

## Stack
Python 3, Flask, mysql-connector-python, OpenAI SDK, python-dotenv.

## Setup
1. Copy `.env.example` (atau buat `.env`) berisi: `GROQ_API_KEY`, `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`
2. `pip install -r requirements.txt`
3. `python app.py` (atau `python app_lokal.py` untuk mode lokal)

## Catatan penting
- `.env` TIDAK di-commit (lihat .gitignore). Kredensial DB & API key hanya lokal.
- Repo: github.com/kandarlubis31/ai-cs-agent (PRIVATE)
