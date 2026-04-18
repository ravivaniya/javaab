# Javaab Project Rules

## Project Overview
Javaab (જવાબ / जवाब) is an AI-powered study assistant for Indian CBSE and
Gujarat Board (GSEB) students, Class 6-12. It supports English, Hindi, and
Gujarati in both native scripts and Roman transliteration.

## Tech Stack
- Backend: Python 3.12, FastAPI, uvicorn, async everywhere
- Web Frontend: Next.js 16+ (App Router), TypeScript, React, Tailwind CSS, framer-motion (for smooth micro-animations), lucide-react (for icons), shadcn/ui
- UI/UX Guidelines: Swiggy-inspired mobile-first design, clean aesthetics, visually premium with vibrant colors (Orange `#FC8019`, Green `#10B981`, Purple `#8B5CF6`)
- Mobile: React Native with Expo (managed workflow)
- Database: Azure Cosmos DB (free tier, serverless)
- Cache: Azure Redis Cache (C0 Basic)
- Search: Azure AI Search (Basic tier, hybrid vector + keyword)
- AI Models: Azure OpenAI (GPT-4.1, GPT-4.1-mini), Azure AI Foundry (Phi-4-mini)
- Embeddings: text-embedding-3-small via Azure OpenAI
- Storage: Azure Blob Storage
- Auth: Azure AD B2C (phone OTP)
- Hosting: Azure Container Apps (backend), Azure Static Web Apps (frontend)

## Code Style Rules
- Python: Follow PEP 8, use type hints everywhere, async/await for all I/O
- TypeScript: Strict mode, no `any` types, use interfaces for objects
- React: Functional components only, hooks, no class components
- Naming: snake_case for Python, camelCase for TypeScript, PascalCase for components
- All API responses: { success, data, error, metadata }
- All environment variables: in .env files, never hardcoded
- Every function must have a docstring/JSDoc comment
- Error handling: Never silently catch errors, always log and return meaningful messages

## Architecture Rules
- Backend: routes → services → repositories (clean architecture)
- Frontend: feature-based folder structure; server components where possible, client components for interactivity (`"use client"`)
- All AI model calls go through central ModelRouter service
- All database operations through repository classes
- Redis: ONLY for verified answer storage (key-value by ID)
- Azure AI Search: ALL similarity matching (HNSW for cache, hybrid for RAG)
- Support 3 languages: en, hi, gu — always use i18n, never hardcode strings

## Security Rules
- Validate all user input with Pydantic (backend) and Zod (frontend)
- Rate limit all endpoints per user tier
- Never expose API keys in frontend code
- Sanitize all user-uploaded images before processing
- All API endpoints require authentication except /health and /auth/*