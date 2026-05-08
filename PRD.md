# Javaab API — B2B AI Infrastructure Platform

## Product Requirements Document

### Curriculum-Aligned AI for Indian Schools & Coaching Institutes

### NCERT (CBSE) + GSEB (Gujarat) · English, Hindi, Gujarati · REST API

---

**Document Version**: 2.0  
**Last Updated**: 2026-05-08  
**Domain**: tryjavaab.com (Cloudflare) → app.tryjavaab.com (Widget) · api.tryjavaab.com (API)

**Current Implementation Snapshot**

- **Backend**: FastAPI mounted at `/health`, `/chat/*`, `/student/*`, `/admin/papers/*`, `/admin/worksheets/*`. API key auth (`X-API-Key` header) on all `/api/v1/*` routes. JWT Bearer auth on all other protected routes.
- **Web widget** (`/web`): Vite + React SPA. Routes: `/`, `/onboarding`, `/chat`, `/settings`, `/admin/papers/*`, `/admin/worksheets/*`.
- **Admin app** (`/admin`): Separate Vite app for managing B2B clients and credit topups — in progress.
- **Active features**: Chat (streaming, RAG, image OCR), Question Paper Generator, Worksheet Builder.
- **Removed**: Phone OTP authentication, Razorpay / B2C subscriptions, referral system, teacher ticket system, Phi-4-mini model.

---

## Table of Contents

**Part A — Product & Business**

1. [Product Vision](#1-product-vision)
2. [B2B Business Model](#2-b2b-business-model)
3. [Client Tiers & API Pricing](#3-client-tiers--api-pricing)
4. [Revenue & Cost Model](#4-revenue--cost-model)
5. [Risk Mitigation](#5-risk-mitigation)

**Part B — Technical Architecture**

6. [Architecture Overview](#6-architecture-overview)
7. [Complete Tech Stack](#7-complete-tech-stack)
8. [AI Models — Selection & Rationale](#8-ai-models)
9. [Knowledge Base & PDF Extraction](#9-knowledge-base)
10. [Multi-Language & Multi-Script Strategy](#10-multi-language-strategy)
11. [Image & OCR Pipeline](#11-image--ocr-pipeline)
12. [RAG Pipeline Design](#12-rag-pipeline-design)
13. [4-Tier Model Routing](#13-4-tier-model-routing)
14. [Verified Answer Bank (Scalable Cache)](#14-verified-answer-bank)
15. [Fallback & Accuracy Safeguards](#15-fallback--accuracy-safeguards)
16. [Domain & URL Architecture](#16-domain--url-architecture)

**Part C — Features**

17. [API Design (v1)](#17-api-design)
18. [White-Label Widget](#18-white-label-widget)
19. [Admin Portal](#19-admin-portal)
20. [Question Paper Generator](#20-question-paper-generator)
21. [Worksheet / DPP Builder](#21-worksheet--dpp-builder)
22. [Master System Prompt](#22-master-system-prompt)
23. [Voice Input (Future Roadmap)](#23-voice-input-future)

**Part D — Execution**

24. [MVP Roadmap](#24-mvp-roadmap)
25. [V1 → V2 Changelog](#25-v1--v2-changelog)

---

## Part A — Product & Business

---

## 1. Product Vision

### The Name: Javaab (જવાબ / जवाब)

"Javaab" means **"Answer"** in both Hindi (जवाब) and Gujarati (જવાબ). Simple, memorable, and instantly communicates the platform's purpose.

### Problem Statement

India has 260M+ school students studying under CBSE (NCERT) and state boards (GSEB). EdTech apps, school ERPs, and coaching management platforms all want AI tutoring features — but building curriculum-aligned AI is expensive, complex, and requires deep domain expertise in Indic languages and pedagogy.

### Solution

Javaab provides a **REST API** that delivers:

- Curriculum-grounded answers (NCERT + GSEB textbooks, Chapter → Section level accuracy)
- Multi-language input/output: English, Hindi, Gujarati — native script AND Roman transliteration
- Image understanding: photograph of a textbook page or handwritten problem → structured answer
- Streaming responses for real-time chat UX
- Pre-built white-label widget for clients who want plug-and-play

Clients integrate once. Students get answers grounded in their actual textbooks.

### Two Delivery Mechanisms

```
┌───────────────────────────────────────────────────────────────┐
│                      JAVAAB PLATFORM                          │
│                                                               │
│  ┌────────────────────────┐    ┌────────────────────────────┐ │
│  │  JAVAAB API            │    │  WHITE-LABEL WIDGET        │ │
│  │  api.tryjavaab.com      │    │  app.tryjavaab.com          │ │
│  │                        │    │                            │ │
│  │  REST API, API key auth │    │  Drop-in React SPA.        │ │
│  │  /api/v1/chat/ask       │    │  Client brands it as their │ │
│  │  /api/v1/papers/*       │    │  own. Fully functional     │ │
│  │  /api/v1/worksheets/*   │    │  chat + paper generator.   │ │
│  │                        │    │                            │ │
│  │  For: EdTech platforms, │    │  For: Schools and coaching │ │
│  │  School ERPs,           │    │  institutes who want a     │ │
│  │  content apps           │    │  complete front-end        │ │
│  └────────────────────────┘    └────────────────────────────┘ │
│                                                               │
│  SHARED: Same knowledge base · Same models · Same RAG         │
└───────────────────────────────────────────────────────────────┘
```

### Non-Negotiables

| Principle              | Meaning                                                                      |
| ---------------------- | ---------------------------------------------------------------------------- |
| **Accuracy**           | Answers grounded in NCERT/GSEB textbooks via RAG; no hallucinations          |
| **Reliability**        | Graceful degradation at every layer; never confidently wrong                 |
| **Curriculum Align**   | Exact terminology, notation, and methods from the actual textbook            |
| **Script Agnostic**    | "trigonometry ka formula" and "ત્રિકોણમિતિ" must both produce equal results   |
| **Latency**            | First token < 1.5 s for cached answers; < 3 s for RAG; < 6 s for complex    |

---

## 2. B2B Business Model

### Who We Sell To

| Segment                       | Size                      | Need                                                      | Purchase Path             |
| ----------------------------- | ------------------------- | --------------------------------------------------------- | ------------------------- |
| **EdTech platforms**          | 500–5,000 students/app    | AI answer engine to embed in their product                | API integration           |
| **Coaching management apps**  | 50–500 students/institute | AI tutor + paper generator inside their ERP              | API or widget             |
| **School ERP vendors**        | 100–2,000 students/school | AI homework help embedded in student portal               | API integration           |
| **Content platforms**         | Large scale               | Curriculum-aligned Q&A generation for their content teams | API batch calls           |

### Why B2B, Not B2C

```
B2C PROBLEMS (why we moved away):
  ✗ High CAC (₹200-500 per student via ads)
  ✗ High churn (students drop after exams)
  ✗ Payment friction (₹199/mo requires UPI/card setup for a 14-year-old)
  ✗ Support overhead (consumer complaints, refunds, GST invoicing per user)

B2B ADVANTAGES:
  ✓ One sale = 50-5,000 end users activated immediately
  ✓ Credit contracts (₹20K-₹2L) paid upfront by institute procurement
  ✓ Low churn (switching costs: API integration, student data, branding)
  ✓ Enterprise invoicing instead of per-user payment processing
  ✓ The institute handles end-user support
```

### Revenue Mechanics

Clients purchase **credit packs** upfront. Each API call consumes credits based on query complexity:

| Query Type             | Credits Consumed | Reasoning                                      |
| ---------------------- | ---------------- | ---------------------------------------------- |
| Text query (cache hit) | 1 credit         | Served from verified answer cache              |
| Text query (RAG)       | 2 credits        | Full retrieval + generation pipeline           |
| Image query            | 4 credits        | OCR extraction + generation                    |
| Paper generation       | 10 credits       | Multi-question generation + formatting         |
| Worksheet generation   | 8 credits        | Multi-exercise generation                      |

---

## 3. Client Tiers & API Pricing

### API Plans

| Feature                          | Starter              | Growth                  | Enterprise               |
| -------------------------------- | -------------------- | ----------------------- | ------------------------ |
| **Monthly credits**              | 5,000                | 50,000                  | Custom                   |
| **Indicative price**             | ₹2,999/mo            | ₹19,999/mo              | Negotiated               |
| **Overage rate**                 | ₹0.80/credit         | ₹0.50/credit            | ₹0.35/credit             |
| **API rate limit**               | 10 req/s             | 50 req/s                | Custom                   |
| **Image input (OCR)**            | ✅                    | ✅                       | ✅                        |
| **Streaming responses**          | ✅                    | ✅                       | ✅                        |
| **Question Paper Generator**     | ❌                    | ✅                       | ✅                        |
| **Worksheet Builder**            | ❌                    | ✅                       | ✅                        |
| **Custom system prompt**         | ❌                    | ✅                       | ✅                        |
| **White-label widget access**    | ❌                    | ✅                       | ✅                        |
| **Institute branding on widget** | ❌                    | ✅                       | ✅                        |
| **Dedicated support**            | Email                | Email + Chat            | Slack / phone            |
| **SLA uptime**                   | Best effort          | 99.5%                   | 99.9%                    |
| **Usage analytics dashboard**    | Basic                | Full                    | Custom export            |

### Credit Pack Pricing (Prepaid)

| Pack          | Credits    | Price (excl. GST) | Rate / credit |
| ------------- | ---------- | ----------------- | ------------- |
| Starter Pack  | 5,000      | ₹3,500            | ₹0.70         |
| Growth Pack   | 25,000     | ₹14,000           | ₹0.56         |
| Scale Pack    | 1,00,000   | ₹45,000           | ₹0.45         |
| Enterprise    | Custom     | Custom            | ₹0.30–₹0.40   |

> All prices + 18% GST. Packs valid 12 months. Unused credits roll over within active contract.

---

## 4. Revenue & Cost Model

### Unit Economics Per Credit

```
COST STRUCTURE (per API query → credits consumed):

Text query, cache hit (1 credit consumed):
  AI cost:    ₹0.10  (GPT-4.1-nano, high cache hit rate)
  Infra:      ₹0.05
  Total cost: ₹0.15
  Revenue:    ₹0.45–₹0.70 (depending on pack)
  Margin:     67–79%

Text query, RAG (2 credits consumed):
  AI cost:    ₹0.50  (GPT-4.1-nano or mini)
  Infra:      ₹0.10
  Total cost: ₹0.60
  Revenue:    ₹0.90–₹1.40
  Margin:     33–57%

Image query (4 credits consumed):
  AI cost:    ₹1.80  (GPT-4.1-mini with vision)
  Infra:      ₹0.15
  Total cost: ₹1.95
  Revenue:    ₹1.80–₹2.80
  Margin:     −8% to 30% (volume discounts eat margin — offset by text queries)

Paper generation (10 credits consumed):
  AI cost:    ₹3.50  (GPT-4.1 full, multi-step)
  Infra:      ₹0.20
  Total cost: ₹3.70
  Revenue:    ₹4.50–₹7.00
  Margin:     18–47%
```

### Revenue Projection — 3 Scale Tiers

#### (a) 5 Active Clients — Launch

| Client                              | Plan       | Monthly Credits | Monthly Revenue |
| ----------------------------------- | ---------- | --------------- | --------------- |
| EdTech app (2,000 students)         | Growth     | 50,000          | ₹19,999         |
| Coaching app (500 students)         | Starter    | 5,000           | ₹2,999          |
| School ERP pilot (200 students)     | Starter    | 5,000           | ₹2,999          |
| Content platform (batch)            | Growth     | 50,000          | ₹19,999         |
| Coaching management SaaS            | Growth     | 50,000          | ₹19,999         |
| **Total Revenue (excl. GST)**       |            |                 | **₹65,995/mo**  |
| **AI + Infra Cost**                 |            |                 | ~₹28,000/mo     |
| **Gross Profit**                    |            |                 | **~₹38,000/mo** |

#### (b) 25 Active Clients — Growth

| Mix                               | Count | Avg Plan Revenue | Monthly Revenue  |
| --------------------------------- | ----- | ---------------- | ---------------- |
| Enterprise clients                | 3     | ₹80,000          | ₹2,40,000        |
| Growth clients                    | 12    | ₹20,000          | ₹2,40,000        |
| Starter clients                   | 10    | ₹3,000           | ₹30,000          |
| **Total Revenue**                 |       |                  | **₹5,10,000/mo** |
| **AI + Infra Cost (~35% margin)** |       |                  | ~₹1,78,500/mo    |
| **Gross Profit**                  |       |                  | **~₹3,31,500/mo**|

#### (c) Path to Scale

```
PATH TO ₹1Cr+/mo ARR:

  Path 1: Enterprise deals (school ERP vendors)
    → 10 enterprise clients × ₹80K/mo = ₹8L/mo
    → Pure volume, low marginal cost (infra scales sub-linearly)

  Path 2: Credit volume growth
    → Cache hit rate improves with scale → margin improves automatically
    → At 35% cache hit rate: ~20% cost reduction

  Path 3: Higher-margin features
    → Paper generation, worksheets = 3-5x credit consumption vs chat
    → Incentivize clients toward these features

  MOST LIKELY: 3-4 anchor enterprise clients + 20-30 growth clients
  by end of Year 1 → ₹50-80L ARR
```

---

## 5. Risk Mitigation

| Risk                             | Mitigation                                                                       |
| -------------------------------- | -------------------------------------------------------------------------------- |
| **Slow B2B sales cycle**         | Offer 30-day free trial (10K credits) + self-service signup, no sales call needed|
| **Client churn after pilot**     | Lock-in via widget branding, student data, paper library stored in our platform  |
| **AI model hallucinations**      | RAG grounding + low temp + confidence scoring + 6-layer fallback                 |
| **Azure cost spikes**            | Per-client rate limits in Redis; DAILY_GLOBAL_CAP circuit breaker                |
| **API key leakage**              | SHA-256 hashed storage; client can rotate instantly via admin portal             |
| **Competition from OpenAI APIs** | Our differentiator: NCERT/GSEB-specific RAG, Indic language tuning, pre-built widget |
| **Single-region outage**         | Central India primary; East US failover for Azure OpenAI                         |

---

## Part B — Technical Architecture

---

## 6. Architecture Overview

```
                        CLOUDFLARE (DNS + CDN + DDoS)
                        ┌────────────────────────────────┐
                        │ tryjavaab.com   → Marketing     │
                        │ app.tryjavaab.com → Widget (B2B) │
                        │ api.tryjavaab.com  → REST API    │
                        │ admin.tryjavaab.com → Admin SPA  │
                        └──────────────┬─────────────────┘
                                       │
┌──────────────────────────────────────────────────────────────────┐
│                      AZURE CLOUD (Central India)                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              AZURE CONTAINER APPS (Auto-scaling)            │  │
│  │                                                             │  │
│  │  FastAPI Backend (Python 3.12, async everywhere)            │  │
│  │  Routes → Services → Repositories (clean architecture)      │  │
│  │  Smart Model Router (3-tier) | RAG Pipeline (hybrid search) │  │
│  │  Cache Service (HNSW + Redis) | Paper & Worksheet Services  │  │
│  └───────────┬──────────────────────┬──────────────────────────┘  │
│              │                      │                             │
│   ┌──────────▼──────┐  ┌────────────▼────────┐  ┌─────────────┐  │
│   │ AZURE AI SEARCH │  │ AZURE REDIS CACHE   │  │ AZURE OPENAI│  │
│   │ Basic → S1      │  │ C0 → C1             │  │             │  │
│   │                 │  │                     │  │ GPT-4.1-nano │  │
│   │ 2 indexes:      │  │ Verified answers    │  │ GPT-4.1-mini│  │
│   │ textbook_chunks │  │ Rate limit counters │  │ GPT-4.1     │  │
│   │ verified_ans    │  │ Credit balances     │  │ text-emb-3s │  │
│   └─────────────────┘  └─────────────────────┘  └─────────────┘  │
│                                                                   │
│  ┌─────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │ Azure Key   │  │ Azure Cosmos DB       │  │ Azure Blob       │  │
│  │ Vault       │  │ (users, conversations,│  │ (PDFs, images,   │  │
│  │ (Secrets)   │  │  messages, bookmarks, │  │  paper exports)  │  │
│  │             │  │  usage_logs, feedback,│  │                  │  │
│  │             │  │  papers, worksheets)  │  │                  │  │
│  └─────────────┘  └──────────────────────┘  └──────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### Services Deferred

| Service                    | Why Not Now                                  | When to Add                  |
| -------------------------- | -------------------------------------------- | ---------------------------- |
| **Azure Event Hub**        | Direct DB write sufficient at current scale  | When Javaab API > 1M req/day |
| **Azure Service Bus**      | Sync request-response fine for <5L users     | When async batch jobs needed |
| **Kubernetes (AKS)**       | Container Apps provides equivalent scaling   | When > 5L users              |
| **Azure API Management**   | Direct FastAPI auth is fine for <50 clients  | When > 50 B2B clients        |

---

## 7. Complete Tech Stack

| Layer                  | Service                        | Tier             | Monthly Cost       | Notes                                |
| ---------------------- | ------------------------------ | ---------------- | ------------------ | ------------------------------------ |
| **DNS/CDN**            | Cloudflare                     | Free             | $0                 | DDoS, SSL, caching                   |
| **Web Widget**         | Azure Static Web Apps + Vite   | Free→Standard    | $0→$9              | app.tryjavaab.com                     |
| **Admin SPA**          | Azure Static Web Apps + Vite   | Free             | $0                 | admin.tryjavaab.com (in progress)     |
| **Backend**            | Azure Container Apps           | Consumption      | ~$0→$50            | Auto-scale to zero                   |
| **Container Registry** | Azure Container Registry       | Basic            | ~$5/mo             | Docker images                        |
| **Secrets**            | Azure Key Vault                | Standard         | ~$0.50/mo          | All API keys, connection strings     |
| **LLM Tier 1**         | GPT-4.1-nano                   | Pay-go           | $0.075/$0.30/1M    | Simple text queries                  |
| **LLM Tier 2**         | GPT-4.1-mini                   | Pay-go           | $0.15/$0.60/1M     | Medium queries + image OCR           |
| **LLM Tier 3**         | GPT-4.1                        | Pay-go           | $2.50/$10.00/1M    | Complex math/science                 |
| **Embeddings**         | text-embedding-3-small         | Pay-go           | $0.02/1M           | Multilingual, all boards             |
| **Vector Search**      | Azure AI Search                | Basic→S1         | $74→$245           | HNSW + keyword hybrid search         |
| **Cache**              | Azure Redis Cache              | C0→C1            | $16→$34            | Credit balances + rate limits + cache|
| **Database**           | Azure Cosmos DB                | Free→Serverless  | $0→$10             | Users, chats, papers, worksheets     |
| **File Storage**       | Azure Blob Storage             | Hot              | ~$2                | PDFs, images, paper/worksheet HTML   |
| **Monitoring**         | Azure Application Insights     | Free (5GB)       | $0                 | Perf, errors, usage                  |
| **Voice (Future)**     | Azure Whisper                  | —                | $0.18-$0.36/hr     | When voice input is added            |

### Cosmos DB Containers

| Container           | Partition Key       | Purpose                                         |
| ------------------- | ------------------- | ----------------------------------------------- |
| `users`             | `/id`               | User/client profiles                            |
| `conversations`     | `/student_id`       | Conversation metadata (title, timestamps)       |
| `messages`          | `/conversation_id`  | Individual messages (query, reply, metadata)    |
| `bookmarks`         | `/user_id`          | Bookmarked messages                             |
| `usage_logs`        | `/user_id`          | Per-query audit trail                           |
| `cache_candidates`  | `/message_id`       | Liked answers flagged for verified cache        |
| `review_tasks`      | `/message_id`       | Auto-flagged low-confidence answers             |
| `feedback`          | `/message_id`       | 👍/👎 feedback records                          |
| `papers`            | `/teacher_id`       | Generated question papers                       |
| `worksheets`        | `/teacher_id`       | Generated worksheets/DPPs                       |

---

## 8. AI Models — Selection & Rationale

### Models Available on Azure AI Foundry

| Model               | Publisher | Input/1M tokens | Output/1M tokens | Vision? | Indic Language Quality |
| ------------------- | --------- | --------------- | ---------------- | ------- | ---------------------- |
| **GPT-4.1-nano** ✅  | OpenAI    | **$0.075**      | **$0.30**        | ❌      | Good for simple tasks  |
| **GPT-4.1-mini** ✅  | OpenAI    | $0.15           | $0.60            | ✅      | Very Good              |
| **GPT-4.1** ✅       | OpenAI    | $2.50           | $10.00           | ✅      | Best                   |
| Llama 4 Maverick    | Meta      | $0.25           | $1.00            | ✅      | Good                   |
| Claude Sonnet       | Anthropic | ~$3.00          | ~$15.00          | ✅      | Good                   |

### Why This Combination

| Our Choice              | Why                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| **GPT-4.1-nano** Tier 1 | 50% cheaper than mini; equally accurate for definitions and factual recall; best Azure integration     |
| **GPT-4.1-mini** Tier 2 | Has vision (nano doesn't); best price-to-quality for concept explanations; excellent Hindi/Gujarati    |
| **GPT-4.1** Tier 3      | Non-negotiable for complex multi-step math/physics numericals. No other model matches it consistently  |
| **NOT Llama 4**         | More expensive than GPT-4.1-mini; less accurate for Hindi/Gujarati math                                |
| **NOT Claude**          | $15/1M output tokens; weaker on NCERT math than GPT-4.1                                               |

---

## 9. Knowledge Base & PDF Extraction

### Source Material

| Board          | Source              | Classes | Languages          | URL                   |
| -------------- | ------------------- | ------- | ------------------ | --------------------- |
| **CBSE/NCERT** | NCERT Textbooks     | 6–12    | English, Hindi     | ncert.nic.in          |
| **CBSE/NCERT** | NCERT Exemplar      | 6–12    | English, Hindi     | ncert.nic.in          |
| **GSEB/GCERT** | GCERT Textbooks     | 6–12    | Gujarati, English  | gcert.gujarat.gov.in  |
| **Both**       | Previous Year Papers| 10, 12  | All                | Board websites        |

### Estimated Knowledge Base Size

| Content                        | Pages       | Chunks       | Tokens   |
| ------------------------------ | ----------- | ------------ | -------- |
| NCERT Textbooks (6-12, EN+HI)  | ~15,000     | ~45,000      | ~22.5M   |
| GSEB Textbooks (6-12, GU+EN)   | ~12,000     | ~36,000      | ~18M     |
| Exemplar + Solutions           | ~5,000      | ~15,000      | ~7.5M    |
| Previous Year Papers           | ~2,000      | ~6,000       | ~3M      |
| **Total**                      | **~34,000** | **~102,000** | **~51M** |

One-time embedding cost: 51M tokens × $0.02/1M = **~$1.02**

### Metadata Schema Per Chunk

```json
{
  "chunk_id": "ncert_c10_sci_ch06_p04_chunk03",
  "content": "The actual text content of this chunk...",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "chapter": 6,
  "chapter_name": "Life Processes",
  "language": "en",
  "source": "ncert_textbook",
  "page_number": 94,
  "embedding": [0.023, -0.041, ...]
}
```

### Chunking Strategy

```
CHUNK SIZE: 300-400 tokens (optimal for retrieval precision)
OVERLAP: 50 tokens (preserve context across chunk boundaries)
SPLITTING: Paragraph-aware (never split mid-sentence or mid-equation)
SPECIAL HANDLING:
  - LaTeX equations: kept whole, not split across chunks
  - Diagrams/figures: separate chunk with alt-text description
  - Numbered lists: entire list in one chunk if < 400 tokens
  - Tables: each row as separate chunk with column headers repeated
```

---

## 10. Multi-Language & Multi-Script Strategy

### The Problem

Indian students mix scripts in a single sentence:
- "Photosynthesis mein CO₂ ka role explain karo" (Hindi + English + chemical formula)
- "ch10 ma trigonometry ना formula" (Gujarati + Roman + chapter reference)

### Our Solution: Language-Agnostic Pipeline

```
STEP 1 — Language Detection (GPT-4.1-nano)
  Detect: English / Hindi / Gujarati / Mixed
  Script: Native (Devanagari/Gujarati) or Roman (transliterated)
  Board inference: GSEB if Gujarati, CBSE if Hindi-only

STEP 2 — Query Normalization
  Transliterated Hindi/Gujarati → Native script via Azure Translator
  Mixed-script → Normalized to primary detected language
  Subject/chapter references → Canonical form

STEP 3 — RAG Retrieval (Language-Aware)
  Query embedding: Multilingual model handles script-mixing natively
  Retrieval: Language filter if confidence > 0.85; else cross-lingual

STEP 4 — Answer Generation
  System prompt enforces: "Reply in the same language the student used"
  Math notation: LaTeX regardless of language (universal)
  Board-specific terms: GSEB uses Gujarati textbook terminology
```

### Transliteration Support

| Input                              | Detected        | Normalized                  |
| ---------------------------------- | --------------- | --------------------------- |
| "photosynthesis explain karo"      | Hindi (Roman)   | फोटोसिंथेसिस explain karo    |
| "trigonometry nu formula batao"    | Gujarati (Roman)| ત્રિકોણમિતિ નું ફૉર્મ્યુલા  |
| "What is Newton's 2nd law"         | English         | What is Newton's 2nd law    |
| "Force = ma समझाओ"                 | Mixed (HI+EN)   | Force = ma समझाओ             |

---

## 11. Image & OCR Pipeline

### Supported Image Types

| Type                    | Example                              | Processing               |
| ----------------------- | ------------------------------------ | ------------------------ |
| Printed textbook page   | NCERT Science Ch.10 page 94          | Direct OCR + RAG         |
| Handwritten question    | Student's notebook problem           | OCR + script normalization|
| Handwritten + printed   | Textbook with student annotations    | Separate extraction      |
| Diagram/figure question | "Explain this diagram"               | Vision description + RAG |
| Multiple questions      | Page with 5 numbered questions       | Extract primary question  |

### Pipeline

```
STEP 1 — Image Preprocessing
  Sanitize: Check MIME type, size < 10MB, strip EXIF
  Resize: Max 1000×1000 px (client-side compression in widget)
  Format: Convert to base64 for API transport

STEP 2 — OCR + Extraction (GPT-4.1-mini with vision)
  Extract: Primary question text
  Detect: Language, script, subject
  Identify: Diagram vs. text question
  Classify: Board (CBSE/GSEB), Class level (if visible)

STEP 3 — Structured Output
  {
    "extracted_text": "...",
    "detected_language": "en|hi|gu",
    "detected_subject": "math|science|...",
    "is_clear": true/false,
    "confidence": 0.0-1.0
  }

STEP 4 — If is_clear = true → RAG pipeline
  If is_clear = false → Ask user to retake photo
```

---

## 12. RAG Pipeline Design

### Two-Stage Retrieval

```
STAGE 1: Verified Answer Cache (Fast Path — ~200ms)
  Index: verified_answers (Azure AI Search, HNSW)
  Check: Has this exact/near-exact question been answered before?
  Threshold: Cosine similarity > 0.92
  Hit → Return cached answer immediately (skip LLM)
  Cache Hit Rate Target: 25% at launch → 40% at 6 months

STAGE 2: Textbook RAG (Standard Path — ~2-4s)
  Index: textbook_chunks (Azure AI Search, hybrid = vector + BM25)
  Top-K: 5 chunks
  Re-rank: by board match, class level, chapter recency
  Augment: System prompt + chunks → Model Router
```

### Hybrid Search Parameters

```python
search_params = {
    "vector_queries": [
        VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=50,
            fields="content_vector"
        )
    ],
    "search_text": normalized_query,      # BM25 keyword component
    "query_type": "semantic",             # Azure AI Search semantic ranker
    "semantic_configuration_name": "curriculum-semantic-config",
    "filter": f"board eq '{board}' and class_level eq {class_level}",
    "select": "chunk_id,content,chapter_name,page_number,subject",
    "top": 5
}
```

### When RAG Fails

```
CONFIDENCE < 0.70 AND no relevant chunks:
  → Tell student: "This isn't in your textbook — try asking your teacher"
  → DO NOT hallucinate
  → Log to review_tasks for content gap analysis
```

---

## 13. 4-Tier Model Routing

```
TIER 0: CACHE HIT (0 LLM tokens)
  Condition: verified_answers similarity > 0.92
  Action: Return cached answer directly
  Cost: ~₹0.05 (retrieval only)

TIER 1: SIMPLE (GPT-4.1-nano)
  Condition: Single-concept definition or factual recall
            No image, No complex calculation
            High confidence RAG (>0.85) with short chunks
  Examples: "What is osmosis?", "Name the layers of the atmosphere"
  Cost: ~₹0.30/query

TIER 2: MEDIUM (GPT-4.1-mini)
  Condition: Multi-step explanation OR image input
            Medium complexity math (1-3 steps)
            Gujarati/Hindi conceptual explanations
  Examples: "Explain the water cycle with a diagram", "Solve 3x + 7 = 22"
  Cost: ~₹0.80/query (text), ~₹2.00/query (image)

TIER 3: COMPLEX (GPT-4.1)
  Condition: Multi-step math/physics numerical
            Proof/derivation required
            Very low RAG confidence (model must reason from principles)
  Examples: "Derive the lens formula", "Solve: Two trains leaving at..."
  Cost: ~₹3.50/query
```

### Routing Decision Logic

```python
def route_query(query: str, has_image: bool, rag_confidence: float, chunks: list) -> str:
    if cache_hit:
        return "cache"
    if has_image:
        return "tier2"  # Vision requires mini at minimum
    if rag_confidence < 0.60 or requires_derivation(query):
        return "tier3"
    if is_simple_factual(query) and rag_confidence > 0.80:
        return "tier1"
    return "tier2"
```

---

## 14. Verified Answer Bank (Scalable Cache)

The verified answer bank is the core moat. Every confident answer that earns a 👍 or passes a quality threshold becomes a cached "fact" that future identical questions retrieve instantly.

### How Answers Enter the Cache

```
PATH 1: Organic (User Feedback)
  Student gives 👍 → Message flagged in cache_candidates
  After 3 likes on same question → Auto-indexed in verified_answers
  Human review (optional) → Admin portal review queue

PATH 2: Batch Seeding (Offline)
  Run scripts/seed_verified_answers.py
  Input: Curated Q&A pairs from textbook solved examples
  Processing: Embed + index in bulk

PATH 3: Teacher Resolution (Future)
  When teacher portal is re-added for B2B custom clients:
  Teacher answer → Immediately indexed in verified_answers
```

### Cache Entry Schema

```json
{
  "id": "verified_c10_sci_photosynthesis_001",
  "question": "What is photosynthesis?",
  "answer": "Photosynthesis is the process by which...",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "chapter": "Life Processes",
  "verified_at": "2026-01-15T10:23:00Z",
  "like_count": 47,
  "question_embedding": [...]
}
```

---

## 15. Fallback & Accuracy Safeguards

### 5-Layer Response Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   RESPONSE PIPELINE                              │
│                                                                  │
│  Layer 1: INPUT VALIDATION                                       │
│    Pydantic models validate all fields                           │
│    Image sanitization (MIME, size, EXIF strip)                  │
│    Rate limit check (Redis counter per API key)                  │
│    Credit balance check (Redis balance > 0)                      │
│                                                                  │
│  Layer 2: CACHE LOOKUP                                           │
│    HNSW similarity search in verified_answers                    │
│    Threshold: cosine > 0.92 → instant return                     │
│    Cache hit rate: 25-40% (grows over time)                      │
│                                                                  │
│  Layer 3: RAG RETRIEVAL                                          │
│    Hybrid search: vector + BM25 + semantic reranker              │
│    Filters: board, class_level, subject                          │
│    Top-5 chunks → Model Router selects LLM                       │
│                                                                  │
│  Layer 4: GENERATION WITH GUARDRAILS                             │
│    Confidence scoring built into system prompt                   │
│    Low confidence (<0.70) → honest "I'm not sure"               │
│    Temperature: 0.3 for factual; 0.5 for explanations            │
│                                                                  │
│  Layer 5: POST-GENERATION CHECKS                                 │
│    Math validation: regex checks for equation balance            │
│    Language check: reply in student's language                   │
│    Citation check: answer references retrieved chunks            │
└─────────────────────────────────────────────────────────────────┘
```

### Confidence Tiers

| Confidence    | Condition                                          | Action                                         |
| ------------- | -------------------------------------------------- | ---------------------------------------------- |
| HIGH (>0.85)  | Strong RAG match, model certainty high              | Return answer with source chapter citation     |
| MEDIUM (0.65) | Partial RAG match                                  | Return answer with "Based on Chapter X" caveat |
| LOW (<0.65)   | Weak RAG, model uncertain                          | "This may be outside your curriculum scope"    |
| UNSURE (<0.50)| No relevant chunks found                           | Honest refusal + suggest alternative resource  |

---

## 16. Domain & URL Architecture

```
tryjavaab.com          → Marketing/landing page (Cloudflare Pages or Static Web App)
app.tryjavaab.com       → White-label widget (B2B clients embed this)
api.tryjavaab.com       → REST API (api.tryjavaab.com/api/v1/*)
admin.tryjavaab.com     → Internal admin portal (client management, credit topups)

TLS: Cloudflare Universal SSL (all subdomains)
CORS: app.tryjavaab.com and admin.tryjavaab.com whitelisted in FastAPI
CDN: Cloudflare caches static assets for widget
```

---

## Part C — Features

---

## 17. API Design

### Authentication

All `/api/v1/*` endpoints require `X-API-Key: <client_api_key>` header.

API keys are:
- 32-byte random hex strings generated at client onboarding
- SHA-256 hashed before storage in Cosmos DB (raw key never stored)
- Stored in Redis for fast per-request validation
- Rotatable by client via admin portal

### Current Endpoints

```
Health
  GET  /health                     → System status (Azure services connectivity)

Chat
  POST /chat/ask                   → Streaming chat (SSE)
  POST /chat/bookmark              → Bookmark a message
  PATCH /chat/{conv_id}/title      → Rename conversation
  PATCH /chat/{conv_id}/message/{msg_id} → Edit + regenerate from message

Student Profile
  POST /student/profile            → Update student profile fields

Question Papers (Admin)
  POST /admin/papers/generate      → Generate multi-variant paper (async)
  GET  /admin/papers               → List papers
  GET  /admin/papers/{id}          → Get paper detail + variants
  GET  /admin/papers/{id}/download → Download paper (HTML/PDF)
  DELETE /admin/papers/{id}        → Soft-delete paper

Worksheets / DPPs (Admin)
  POST /admin/worksheets/generate  → Generate worksheet (async)
  GET  /admin/worksheets           → List worksheets
  GET  /admin/worksheets/{id}      → Get worksheet detail
  GET  /admin/worksheets/{id}/download → Download worksheet
  DELETE /admin/worksheets/{id}    → Soft-delete worksheet
```

### `/chat/ask` Request Schema

```json
{
  "query": "What is photosynthesis?",
  "user_id": "student_123",
  "image_base64": null,
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "language": "en",
  "conversation_id": "conv_abc123",
  "retry_of": null
}
```

### `/chat/ask` Response (Server-Sent Events)

```
data: {"type": "chunk", "content": "Photosynthesis is the"}
data: {"type": "chunk", "content": " process by which..."}
data: {"type": "metadata", "model": "gpt-4.1-nano", "confidence": "high", "from_cache": false}
data: {"type": "sources", "sources": [{"chapter": "Life Processes", "page": 94}]}
data: {"type": "conversation_id", "id": "conv_abc123"}
data: [DONE]
```

### Future `/api/v1/*` Endpoints (B2B API)

These will be the publicly documented API surface once the API management layer is in place:

```
POST /api/v1/chat/ask             → Same as /chat/ask but API-key auth + credit deduction
POST /api/v1/papers/generate      → Paper generation with credit deduction
POST /api/v1/worksheets/generate  → Worksheet generation with credit deduction
GET  /api/v1/usage                → Credit balance + usage breakdown
```

---

## 18. White-Label Widget

The `/web` Vite React SPA is the white-label widget for B2B clients who want a complete front-end without building one.

### Current Frontend Routes

| Route                    | Component             | Description                                |
| ------------------------ | --------------------- | ------------------------------------------ |
| `/`                      | Index                 | Landing / auth gate                        |
| `/onboarding`            | Onboarding            | 6-step first-run flow (board, class, lang) |
| `/chat`                  | Chat                  | Main streaming chat interface              |
| `/settings`              | Settings              | Profile, study settings, appearance        |
| `/admin/papers`          | PapersList            | List generated papers                      |
| `/admin/papers/new`      | CreatePaper           | Paper generation form                      |
| `/admin/papers/:id`      | PaperDetail           | Paper variants + download                  |
| `/admin/worksheets`      | WorksheetsList        | List generated worksheets                  |
| `/admin/worksheets/new`  | CreateWorksheet       | Worksheet generation form                  |
| `/admin/worksheets/:id`  | WorksheetDetail       | Worksheet detail + download                |

### Widget Configuration

B2B clients can configure the widget for their brand via environment variables:

```env
VITE_API_URL=https://api.tryjavaab.com
VITE_BRAND_NAME=My Coaching App
VITE_BRAND_LOGO_URL=https://myclient.com/logo.png
VITE_PRIMARY_COLOR=#FF6B00
VITE_DEFAULT_BOARD=GSEB
VITE_DEFAULT_CLASS=10
```

### Auth Model for Widget

The widget currently uses a JWT Bearer token model (stored in `localStorage`). For B2B deployments, the client application issues JWTs to their students and passes them to the widget.

---

## 19. Admin Portal

The `/admin` directory contains a separate Vite SPA for Javaab internal operations and B2B client management.

### Admin Features (Planned)

```
CLIENT MANAGEMENT:
  ✓ Create new B2B client accounts
  ✓ Generate + rotate API keys
  ✓ Set rate limits per client
  ✓ Configure per-client system prompt overrides

BILLING:
  ✓ Credit topup (manual for now, Stripe/Razorpay later)
  ✓ Usage dashboard per client (queries by type, date range)
  ✓ Low-credit alerts configuration

CONTENT MANAGEMENT:
  ✓ Review flagged answers (review_tasks queue)
  ✓ Approve answers into verified cache
  ✓ Batch seed verified answers from curated Q&A CSVs

ANALYTICS:
  ✓ Daily query volume by client
  ✓ Cache hit rate trends
  ✓ Model usage distribution (Tier 1/2/3 split)
  ✓ Subject/board/class breakdown
```

---

## 20. Question Paper Generator

B2B clients (Growth/Enterprise plans) can generate NCERT/GSEB-aligned question papers.

### Paper Configuration

```json
{
  "title": "Class 10 Science — Chapter 6 Mid-Term Test",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "chapters": [6, 7],
  "total_marks": 30,
  "duration_minutes": 60,
  "question_types": {
    "mcq": 5,
    "short_answer": 5,
    "long_answer": 3
  },
  "difficulty": "medium",
  "variants": 2,
  "language": "en"
}
```

### Generation Pipeline

```
STEP 1: Question Mining (RAG)
  → Retrieve relevant chunks for specified chapters
  → Extract learnable concepts and key facts

STEP 2: Question Generation (GPT-4.1)
  → Generate questions by type and difficulty
  → Ensure bloom's taxonomy distribution
  → Include answer key with mark scheme

STEP 3: Variant Generation (if variants > 1)
  → Shuffle MCQ options
  → Paraphrase questions for different variants
  → Same answer key, different ordering

STEP 4: Formatting
  → Render to styled HTML (print-ready)
  → Include header: school name, class, subject, date, duration
  → Export: HTML (immediate) + PDF (via Puppeteer, future)

STEP 5: Storage
  → Save to Cosmos DB papers container
  → Paper available for re-download until soft-deleted
```

---

## 21. Worksheet / DPP Builder

Similar to the paper generator but optimized for Daily Practice Problems (DPPs) and focused topic worksheets.

### Worksheet Configuration

```json
{
  "title": "Trigonometry Practice — Class 10 Math",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Mathematics",
  "topic": "Trigonometric Identities",
  "num_questions": 15,
  "difficulty_mix": {"easy": 5, "medium": 7, "hard": 3},
  "include_solution_hints": true,
  "language": "en"
}
```

---

## 22. Master System Prompt

The system prompt is the core quality guardrail. It runs on every generation request.

```
You are Javaab, an AI study assistant for Indian school students (Class 6-12).

KNOWLEDGE CONSTRAINTS:
- Answer ONLY based on the textbook chunks provided in this context
- If the answer is not in the provided context, say clearly:
  "I couldn't find a definitive answer in the textbook. Please check Chapter [X] or ask your teacher."
- Never fabricate facts, formulas, or examples

CURRICULUM ALIGNMENT:
- Follow the exact terminology used in NCERT/GSEB textbooks
- Use the same notation and methods taught at this class level
- Example: Class 8 uses "photosynthesis formula" from NCERT Science Chapter 1 — do not use university-level biochemistry

LANGUAGE:
- Detect the student's language from their query
- Reply in the SAME language (English / Hindi / Gujarati / Mixed)
- For Hindi/Gujarati: use native script if the student used it; Roman if they used Roman
- Math and formulas: always LaTeX format regardless of language

FORMATTING:
- Step-by-step for procedural answers (numbered steps)
- LaTeX for all math ($..$ for inline, $$...$$ for display)
- Short, clear language — assume Class 8-10 reading level

CONFIDENCE:
- Always end with your confidence: [HIGH / MEDIUM / LOW]
- LOW confidence: add "Please verify with your textbook or teacher"
```

---

## 23. Voice Input (Future)

Voice input will be added post-launch when demand justifies the Azure Whisper cost.

```
PLANNED PIPELINE:
  1. Browser MediaRecorder API → audio blob → base64
  2. POST /chat/voice → Azure Whisper → transcript
  3. Transcript → existing chat pipeline (no changes needed downstream)
  4. Response: same SSE stream as text queries

LANGUAGES:
  Azure Whisper supports Hindi and English natively
  Gujarati: Use general multilingual model (lower accuracy — test before shipping)

COST:
  Azure Whisper: $0.18-$0.36/hour of audio
  Average student query: ~5 seconds = ~$0.0003 per voice query
  Negligible compared to LLM cost
```

---

## Part D — Execution

---

## 24. MVP Roadmap

### Phase 1 — Core API (Complete ✓)

- [x] FastAPI backend with JWT auth middleware
- [x] RAG pipeline (hybrid search + verified cache)
- [x] 3-tier model routing (nano/mini/full)
- [x] Streaming chat endpoint (`/chat/ask`)
- [x] Image OCR pipeline
- [x] Multi-language support (EN/HI/GU)
- [x] Question Paper Generator
- [x] Worksheet/DPP Builder
- [x] White-label widget (React SPA)
- [x] Azure infrastructure (Cosmos DB, Redis, AI Search, Blob)

### Phase 2 — B2B Platform (In Progress)

- [ ] `/api/v1/*` API layer with API key auth
- [ ] Credit balance tracking in Redis
- [ ] Per-request credit deduction
- [ ] Admin portal for client management
- [ ] API key management (create, rotate, revoke)
- [ ] Usage dashboard per client
- [ ] Rate limiting per API key (configurable)

### Phase 3 — Scale

- [ ] Azure API Management layer
- [ ] Webhook notifications (low credit, usage milestones)
- [ ] Batch paper/worksheet generation queue
- [ ] PDF export via headless Chrome
- [ ] WhatsApp Business API alerts for critical events
- [ ] Billing automation (Stripe or manual bank transfer)

### Phase 4 — Product Expansion

- [ ] Voice input (Azure Whisper)
- [ ] Subject browser UI
- [ ] Progress tracking per student
- [ ] Analytics dashboards for B2B clients
- [ ] Custom knowledge base injection (client can add their own study material)

---

## 25. V1 → V2 Changelog

### V2.0 — B2B Pivot (2026-05-08)

**Removed (B2C features, entire feature families deleted):**
- Phone OTP authentication (`/auth/login`, `/auth/verify`, `/auth/register`, `/auth/profile`)
- Razorpay / B2C subscription flow (payment_service.py, Subscribe page, SettingsSubscription)
- Referral system (referral_service.py, Refer page, referral tracking in Cosmos DB)
- Teacher ticket system as a B2C user feature (ticket_service.py, /tickets routes, /admin/tickets routes, all Ticket UI)
- Phi-4-mini model (was being trialled, replaced by GPT-4.1-nano before removal)
- B2C plan pricing (Free/Plus/Pro subscription tiers)

**Updated:**
- Frontend routes: removed `/login`, `/tickets`, `/subscribe`, `/refer`, `/settings/subscription`, `/admin/teacher/*`
- Papers and Worksheets moved from `/admin/teacher/papers` to `/admin/papers` (no teacher role restriction)
- `app/config.py`: removed `AUTH_MODE`, `MOCK_OTP`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`
- `auth_middleware.py`: removed auth routes from `PUBLIC_PATHS`
- `cosmos_repo.py`: removed `CONTAINER_TICKETS`, `CONTAINER_REFERRALS`, 10 deprecated methods
- `.env.example`: removed deprecated vars

**Architecture direction:**
- Auth pivot: from phone OTP + JWT → API key (`X-API-Key`) for `/api/v1/*`
- Business pivot: from B2C subscriptions → B2B credit packs
- Revenue pivot: from ₹199/₹499/mo per student → ₹3,000–₹80,000/mo per B2B client

### V1.1 (2026-04-30)

- Prevent overwriting existing user profiles on re-login
- Profile caching improvements
- HTTPS enforcement for API URL construction
- Question paper generator added
- Dark theme support
- TODO system improvements
