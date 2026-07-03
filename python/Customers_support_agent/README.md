# AI Customer Support Agent

A production-ready, RAG-powered customer support agent: upload your documents
(PDF / DOCX / TXT / MD), ask questions in a chat UI, and get answers grounded
in — and cited from — your own knowledge base.

**Stack:** FastAPI · Mistral LLM (via LangChain) · Qdrant Cloud (vector DB,
raw `qdrant-client`) · HuggingFace `sentence-transformers` embeddings ·
WebSocket streaming · vanilla HTML/CSS/JS front end.

---

## 1. Project structure

```
customer-support-agent/
├── main.py                     # FastAPI app factory + entrypoint object
├── requirements.txt
├── .env.example                # copy to .env and fill in secrets
├── app/
│   ├── config.py                # typed Settings (pydantic-settings)
│   ├── dependencies.py          # DI wiring / singletons
│   ├── api/                     # route handlers
│   │   ├── chat.py               # POST /api/chat, DELETE /api/chat/{id}
│   │   ├── health.py             # GET  /api/health
│   │   ├── upload.py             # POST /api/upload
│   │   └── websocket.py          # WS   /ws/chat  (streaming)
│   ├── core/
│   │   ├── exceptions.py         # typed app exception hierarchy
│   │   └── logging_config.py     # console + rotating file logging
│   ├── models/
│   │   └── schemas.py            # Pydantic request/response models
│   ├── services/
│   │   ├── document_processor.py # load + chunk PDF/DOCX/TXT/MD
│   │   ├── embeddings.py         # HuggingFace embedding wrapper
│   │   ├── llm_service.py        # Mistral chat + streaming
│   │   ├── memory.py             # bounded per-session chat history
│   │   ├── rag_pipeline.py       # retrieval + context compression + LLM
│   │   └── vector_store.py       # Qdrant upsert / similarity / MMR search
│   └── utils/
│       ├── file_validation.py    # extension/size checks, safe paths
│       └── security.py           # filename/input/session sanitizing
├── templates/index.html         # chat UI shell
├── static/
│   ├── css/style.css
│   └── js/chat.js                # WebSocket client, upload, rendering
├── uploads/                     # transient storage during ingestion
└── logs/                        # rotating app.log
```

## 2. Prerequisites

- Python 3.11+
- A **Mistral API key** — https://console.mistral.ai
- A **Qdrant Cloud** cluster (free tier is fine) — https://cloud.qdrant.io
  (grab the cluster URL and API key)

## 3. Setup

```bash
cd customer-support-agent

# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
# then edit .env and fill in MISTRAL_API_KEY, QDRANT_URL, QDRANT_API_KEY
```

> The first run downloads the `sentence-transformers/all-MiniLM-L6-v2`
> embedding model (~90 MB) from HuggingFace — this needs an internet
> connection once, then it's cached locally.

## 4. Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

- Drag & drop (or browse) a PDF/DOCX/TXT/MD file into the sidebar to index it.
- Ask a question in the chat box — answers stream in over WebSocket and each
  response shows the exact source chunks used.
- "New conversation" clears that browser session's memory (`DELETE
  /api/chat/{session_id}`).

Health check: `GET /api/health` → `{"status": "ok", "vector_store_connected": true, ...}`

## 5. Configuration reference (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `MISTRAL_API_KEY` | — (required) | Mistral API secret key |
| `MISTRAL_MODEL` | `mistral-large-latest` | Chat model id |
| `QDRANT_URL` | — (required) | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | — (required) | Qdrant Cloud API key |
| `QDRANT_COLLECTION_NAME` | `support_agent_docs` | Collection name (auto-created) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HF embedding model |
| `EMBEDDING_DIMENSION` | `384` | Must match the embedding model's output size |
| `MAX_UPLOAD_SIZE_MB` | `20` | Per-file upload cap |
| `ALLOWED_EXTENSIONS` | `.pdf,.txt,.docx,.md` | Allowed upload types |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Text splitter tuning |
| `RETRIEVAL_TOP_K` | `5` | Chunks returned per query |
| `MMR_FETCH_K` / `MMR_LAMBDA` | `20` / `0.5` | MMR candidate pool / relevance-diversity trade-off |
| `MAX_HISTORY_TURNS` | `10` | Conversation turns kept in memory per session |

## 6. Notes on design decisions

- **Qdrant is used directly** via `qdrant-client` (no LangChain vector-store
  wrapper) so MMR re-ranking and payload shape are fully under app control.
- **Uploaded files are transient**: they're written to `uploads/`, parsed,
  embedded, upserted into Qdrant, then deleted — Qdrant is the durable store.
- **All secrets load from environment variables** (`app/config.py`); nothing
  is hard-coded, and placeholder values are rejected at startup.
- **Global exception handling** (`main.py`) converts known `SupportAgentError`
  subclasses into clean JSON with the right status code, and never leaks
  internal stack traces to the client for unexpected errors.

## 7. Troubleshooting

- **"A required secret is missing or still set to its placeholder value"**
  → you haven't filled in `.env` yet (still has `your_..._here`).
- **Vector store connection fails at startup** → check `QDRANT_URL` scheme
  (should start with `https://`) and that the API key is correct.
- **Chat page loads but WebSocket never connects** → make sure you're running
  via `uvicorn`, not opening `templates/index.html` as a static file directly.
