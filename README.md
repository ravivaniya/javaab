# Javaab API — B2B AI Infrastructure for Indian Schools

Javaab provides curriculum-aligned AI (NCERT + GSEB) as a REST API for schools and coaching institutes. Clients integrate via API key or deploy our white-label chat widget.

## Structure

| Directory  | Description                                                                             |
| ---------- | --------------------------------------------------------------------------------------- |
| `backend/` | FastAPI service — `/chat/ask`, `/student/profile`, `/admin/papers`, `/admin/worksheets` |
| `web/`     | White-label chat widget (React/Vite) — deployed by B2B clients in their apps            |
| `admin/`   | Internal admin portal (React/Vite) — client management, API key issuance, credit topups |
| `scripts/` | Data ingestion, textbook chunk indexing, and cache-building scripts                     |

## Quick Start

```bash
# Backend
cd backend
cp .env.example .env   # fill in Azure credentials
uv sync
uvicorn app.main:app --reload

uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# White-label widget
cd web
npm install
npm run dev

# Admin portal
cd admin
npm install
npm run dev
```

## Infrastructure

See [AZURE_SETUP.md](AZURE_SETUP.md) for the full Azure provisioning guide (Cosmos DB, Redis, AI Search, Azure OpenAI, Container Apps).
