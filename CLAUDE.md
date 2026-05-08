# Javaab Project Rules (B2B API Pivot)

## Project Overview

Javaab API is a B2B AI infrastructure platform for Indian schools and coaching institutes. We provide curriculum-aligned AI (NCERT + GSEB) via REST API. Clients integrate our API into their own apps OR purchase our white-label widget.

## Architecture

- /backend → FastAPI service exposing /api/v1/\* endpoints (API key auth)
- /web → White-label widget (existing Vite app, being repurposed for B2B clients)
- /admin → NEW separate Vite admin app for managing clients + credit topups
- /scripts → ingestion, seeding, maintenance scripts

## Tech Stack

- Backend: Python 3.12, FastAPI, async everywhere, httpx for HTTP
- Database: Azure Cosmos DB (clients, ledger, conversations)
- Cache/Counter: Azure Redis (live credit balance, rate limits)
- Search: Azure AI Search (textbook_chunks + verified_answers indexes, HNSW)
- LLM Tier 1 (simple): GPT-4.1-nano via Azure OpenAI
- LLM Tier 2 (medium + image): GPT-4.1-mini via Azure OpenAI
- LLM Tier 3 (complex): GPT-4.1 via Azure OpenAI
- Embeddings: text-embedding-3-small via Azure OpenAI
- Auth: API key (X-API-Key header) for all /api/v1/\* routes
- Notifications: WhatsApp Business API for alerts

## Removed (do not reference these in any new code)

- Phone OTP authentication
- Razorpay / B2C subscription flow
- Referral system
- Teacher ticket system
- Phi-4-mini (replaced by GPT-4.1-nano)

## Code Style

- Python: PEP 8, type hints everywhere, async I/O
- TypeScript: strict mode, no `any`, interfaces for shapes
- React: functional components, hooks only
- Naming: snake_case (Python), camelCase (TS), PascalCase (components)
- All env vars in .env, never hardcoded
- Every function has a docstring/JSDoc
- Errors: never silently catch, always log with context

## Backend Architecture Rules

- routes/ → services/ → repositories/ (clean architecture)
- All AI model calls go through ModelRouter
- All DB ops through repository classes
- Redis: live credit balance counter + rate limits
- Cosmos DB: append-only credit ledger + clients + conversations
- Azure AI Search: ALL similarity matching (HNSW for cache, hybrid for RAG)

## Security

- Validate input with Pydantic
- API keys hashed (SHA-256) before storage; never store raw keys
- Rate limit per API key (configurable per client)
- Sanitize all user-uploaded images
- All /api/v1/\* routes require valid API key
- Log every API call with request_id for audit
