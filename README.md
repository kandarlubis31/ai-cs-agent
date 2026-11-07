# ai-cs-agent

A small Flask customer-service chatbot that answers product questions using an LLM, grounded
in the store's own catalogue from MySQL.

## How it works

- `app.py` exposes a Flask app with a chat page and a JSON endpoint.
- The LLM is reached through the **OpenAI SDK pointed at Groq**
  (`https://api.groq.com/openai/v1`), default model `llama-3.3-70b-versatile`.
- Product data is read from a MySQL table (`products`, first 50 rows) and injected into the
  prompt, so answers reflect real stock rather than the model's imagination.
- Conversation memory is kept per session in an in-process dict, capped at
  **6 turns** (`MAX_HISTORY_TURNS`).
- Input is truncated to **500 characters** (`MAX_INPUT_LENGTH`) to keep prompts bounded.
- `RateLimitError` from the provider is caught and answered with a friendly Indonesian
  fallback instead of a stack trace.
- `app_lokal.py` is a variant for running locally without the full configuration.
- Every required environment variable is checked at import time and logged if missing, so
  misconfiguration shows up immediately instead of on the first request.

## Requirements

- Python 3.10+
- MySQL (or MariaDB) with a `products` table

## Setup

1. Copy the environment template and fill it in:

```bash
cp .env.example .env
```

Required variables:

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Groq API key |
| `DB_HOST` | MySQL host |
| `DB_USER` | MySQL user |
| `DB_PASS` | MySQL password |
| `DB_NAME` | Database name |

2. Install and run:

```bash
pip install -r requirements.txt
python app.py
```

Use `python app_lokal.py` for the local variant.

## Notes

- `.env` is git-ignored. No credentials are stored in the repository.
- Sessions live in memory, so restarting the process clears every conversation. Fine for a
  demo; use a real session store if you run it under multiple workers.

---

## Bahasa Indonesia

**ai-cs-agent** adalah chatbot layanan pelanggan berbasis Flask yang menjawab pertanyaan produk memakai LLM, dengan jawaban berpijak pada katalog toko yang tersimpan di MySQL.

---

## License

MIT
