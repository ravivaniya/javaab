# Javaab — AI-Powered Education Platform

## Complete Technical Plan V1

### Products: Javaab AI (Chat) + Javaab API (Developer Platform)

### Class 6–12 | NCERT (CBSE) + GSEB (Gujarat) | English, Hindi, Gujarati

### Azure Cloud | Vite (React SPA) | React Native | Swiggy-Style Design

---

**Document Version**: 1.0
**Last Updated**: 2026-04-21
**Domain**: tryjavaab.com (Cloudflare) → app.tryjavaab.com (Web App)

**Current Implementation Snapshot**

- Web app: Vite + React SPA with React Router routes for `/`, `/login`, `/onboarding`, `/chat`, `/tickets`, `/tickets/:id`, `/subscribe`, `/refer`, `/settings`, `/settings/subscription`, and `/admin/teacher/*`.
- Backend: FastAPI mounted routes for `/health`, `/auth/*`, `/chat/*`, `/subjects/*`, `/tickets/*`, `/admin/*`, and `/student/profile`.
- Subject browser is a future/backlog UI. The backend subject endpoints exist so the frontend can add this screen later without another API contract change.

---

## Table of Contents

**Part A — Product & Business**

1. [Product Vision](#1-product-vision)
2. [Query Counting — How We Count & Bill](#2-query-counting)
3. [Plan Structure & Pricing (with GST)](#3-plan-structure--pricing)
4. [Referral & Discount System](#4-referral--discount-system)
5. [Payment Gateway (Razorpay)](#5-payment-gateway-razorpay)
6. [Cost Estimate — 3 Scale Tiers](#6-cost-estimate)
7. [Break-Even Formulas & Calculator](#7-break-even-formulas)
8. [Risk Mitigation](#8-risk-mitigation)

**Part B — Technical Architecture**

9. [Architecture Overview](#9-architecture-overview)
10. [Complete Tech Stack](#10-complete-tech-stack)
11. [AI Models — Selection & Rationale](#11-ai-models)
12. [Knowledge Base & PDF Extraction](#12-knowledge-base)
13. [Multi-Language & Multi-Script Strategy](#13-multi-language-strategy)
14. [Image & OCR Pipeline](#14-image--ocr-pipeline)
15. [RAG Pipeline Design](#15-rag-pipeline-design)
16. [4-Tier Model Routing](#16-4-tier-model-routing)
17. [Verified Answer Bank (Scalable Cache)](#17-verified-answer-bank)
18. [6-Layer Fallback + Teacher Ticket (Pro Only)](#18-6-layer-fallback--teacher-ticket)
19. [Accuracy & Reliability Safeguards](#19-accuracy--reliability-safeguards)
20. [Domain & URL Architecture](#20-domain--url-architecture)

**Part C — Features**

21. [Master System Prompt](#21-master-system-prompt)
22. [Frontend Architecture (Vite + React Native)](#22-frontend-architecture)
23. [API Design](#23-api-design)
24. [Custom Plan — Coaching/School Features](#24-custom-plan)
25. [Javaab API — Developer Platform (Future)](#25-javaab-api)
26. [Voice Input (Future Roadmap)](#26-voice-input-future)

**Part D — Execution**

27. [MVP Roadmap](#27-mvp-roadmap)
28. [Student & Teacher Cheat Sheet](#28-student--teacher-cheat-sheet)
29. [V2 → V3 Changelog](#29-v2--v3-changelog)
30. [Vibe Coding Playbook — Zero to Launched App in 30 Days](#30-vibe-coding-playbook)

---

## Part A — Product & Business

---

## 1. Product Vision

### The Name: Javaab (જવાબ / जवाब)

"Javaab" means **"Answer"** in both Hindi (जवाब) and Gujarati (જવાબ). It's simple, memorable, and instantly communicates the app's purpose to every Indian student.

### Problem Statement

Students in India studying under CBSE (NCERT) and Gujarat State Board (GSEB/GCERT) from Class 6 to 12 face difficulties understanding textbook concepts, solving problems, and getting instant, reliable help — especially in vernacular languages and from non-English-medium backgrounds.

### Solution

An AI-powered educational assistant that:

- Accepts **text** (typed) or **image** (photo of textbook/notebook) input
- Understands questions in **English, Hindi, and Gujarati** — in both native scripts (Devanagari, Gujarati) AND Roman/transliterated script
- Returns **curriculum-aligned, step-by-step answers** grounded in actual NCERT and GSEB textbook content
- Works on **mobile** (React Native) and **web** (Vite + React)
- Runs entirely on **Microsoft Azure**

### Non-Negotiables

| Principle                | Meaning                                                                         |
| ------------------------ | ------------------------------------------------------------------------------- |
| **Accuracy**             | Answers MUST be grounded in official textbook content via RAG; no hallucination |
| **Reliability**          | System must gracefully degrade, never give a confidently wrong answer           |
| **Curriculum Alignment** | Follow the exact terminology, methods, and notation used in NCERT/GSEB books    |
| **Script Agnostic**      | "trigonometry ka formula batao" and "ત્રિકોણમિતિનું સૂત્ર" must both work       |

### Two Products Under One Brand

```
┌──────────────────────────────────────────────────────────────┐
│                      JAVAAB PLATFORM                          │
│                                                               │
│  ┌─────────────────────────┐  ┌────────────────────────────┐  │
│  │     JAVAAB AI           │  │     JAVAAB API             │  │
│  │     (NOW — V1 Launch)   │  │     (FUTURE — After        │  │
│  │                         │  │      success of Javaab AI) │  │
│  │  Chat-based study       │  │                            │  │
│  │  assistant for students │  │  API service for EdTech    │  │
│  │  and coaching institutes│  │  developers to integrate   │  │
│  │                         │  │  Javaab's curriculum-      │  │
│  │  Users: Students,       │  │  aligned AI into their     │  │
│  │  Teachers, Coaching     │  │  own apps                  │  │
│  │  Classes                │  │                            │  │
│  │                         │  │  Users: EdTech startups,   │  │
│  │  Access: Web + Mobile   │  │  School ERP vendors,       │  │
│  │  URL: app.tryjavaab.com   │  │  Content platforms         │  │
│  │                         │  │                            │  │
│  │  Revenue: Subscription  │  │  Access: REST API          │  │
│  │  (B2C + B2B)            │  │  URL: api.tryjavaab.com       │  │
│  │                         │  │  Revenue: Pay-per-query    │  │
│  │                         │  │  (B2B)                     │  │
│  └─────────────────────────┘  └────────────────────────────┘  │
│                                                               │
│  SHARED INFRASTRUCTURE:                                       │
│  Same knowledge base, same AI models, same RAG pipeline,      │
│  same verified cache — just different interfaces               │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Query Counting — How We Count & Bill

### Counting Scenarios

```
SCENARIO 1: Student types "What is photosynthesis?"
→ 1 query (simple text)

SCENARIO 2: Student scans a textbook page with 1 question
→ 1 query (image extraction + answer)

SCENARIO 3: Student asks "What is photosynthesis?" then follows up
            "Explain step 3 in more detail"
→ 2 queries (each message in the conversation = 1 query)

SCENARIO 4: Student scans a page with 5 questions visible
→ 1 query (we answer only the primary question detected)
→ If student asks about each separately = 5 queries total

SCENARIO 5: Student scans + also types text along with image
→ 1 query (image + text together = single query)
```

### Our Approach: Per Interaction (Message-Based)

| Approach             | Pros                                                         | Cons                                                                   | Our Choice?       |
| -------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- | ----------------- |
| **Token-based**      | Most precise                                                 | Complex for users; "How many tokens is my question?" confuses students | ❌                |
| **Session-based**    | Simple; encourages follow-ups                                | Gameable; one session could have 100 messages                          | ❌                |
| **Message-based** ✅ | Simple, predictable, transparent: "You have 87 queries left" | A simple "hi" costs same as a complex math problem                     | **✅ YES**        |
| **Weighted message** | Fairer to users                                              | Complex to implement and explain                                       | ❌ (future maybe) |

### Why Message-Based is Best for Javaab

```
FOR STUDENTS: Easy to understand
  "You have 50 free questions this month"
  Not: "You have 500,000 tokens remaining" (confusing!)

FOR US: Easy to implement & track
  Every POST /chat/ask = increment query_count by 1
  No need to pre-estimate token costs per query

FOR BILLING: Predictable
  We know average cost per query (~₹0.83)
  We can price plans knowing average usage patterns

FOR SCALING: Simple rate limiting
  Redis counter per user: INCR user:{id}:monthly_queries
  Check against plan limit before processing

THE TRADE-OFF:
  A student asking "Hi" costs us ~₹0.05 (cache hit or simple)
  A student asking complex physics = ~₹3.50
  On AVERAGE across all queries: ~₹0.83 per query
  This averages out across thousands of users ✅
```

### Query Counting Rules

```
COUNTS AS 1 QUERY:
  ✓ Any text message sent by student
  ✓ Any image sent (with or without text)
  ✓ Any follow-up message in a conversation
  ✓ A "regenerate" request (student asks to re-answer)

DOES NOT COUNT AS A QUERY:
  ✗ Viewing conversation history
  ✗ Browsing subjects/chapters
  ✗ Giving feedback (👍/👎)
  ✗ Changing settings/profile
  ✗ Viewing teacher ticket responses
  ✗ System messages (rate limit warnings, tips)
```

---

## 3. Plan Structure & Pricing

### Javaab AI Plans

| Feature                      | Free   | Plus (For Curious)                 | Pro (For Serious)                   | Custom (Schools/Coaching) |
| ---------------------------- | ------ | ---------------------------------- | ----------------------------------- | ------------------------- |
| **Price (incl. GST)**        | ₹0     | ~~₹499~~ **₹199/mo**               | ~~₹999~~ **₹499/mo**                | Based on formula          |
| **Annual Price**             | ₹0     | ~~₹5,988~~ **₹1,899/yr** (20% off) | ~~₹11,988~~ **₹4,791/yr** (20% off) | Negotiated                |
| **Queries/month**            | 50     | 1,000                              | Unlimited                           | Custom formula            |
| **Text input**               | ✅     | ✅                                 | ✅                                  | ✅                        |
| **Image input**              | ❌     | ✅                                 | ✅                                  | ✅                        |
| **Voice input**              | ❌     | ❌                                 | 🔜 Future                           | 🔜 Future                 |
| **Streaming answers**        | ✅     | ✅                                 | ✅                                  | ✅                        |
| **LaTeX math**               | ✅     | ✅                                 | ✅                                  | ✅                        |
| **Conversation history**     | 7 days | 90 days                            | Unlimited                           | Unlimited                 |
| **Priority processing**      | ❌     | ❌                                 | ✅ (dedicated queue)                | ✅                        |
| **Teacher Tickets**          | ❌     | ❌                                 | ✅ (3/month)                        | ✅ (based on plan)        |
| **Exam tips**                | Basic  | Full                               | Full + PYQ analysis                 | Full + Custom             |
| **Question Paper Generator** | ❌     | ❌                                 | ❌                                  | ✅                        |
| **Lesson Plan Builder**      | ❌     | ❌                                 | ❌                                  | ✅                        |
| **Institute Branding**       | ❌     | ❌                                 | ❌                                  | ✅ (logo, name, header)   |
| **Referral rewards**         | ✅     | ✅                                 | ✅                                  | ✅                        |
| **API access**               | ❌     | ❌                                 | ❌                                  | 🔜 Javaab API (future)    |

### Pricing Viability Check

```
COST PER QUERY (weighted average): ₹0.83

FREE PLAN (50 queries/month):
  Cost to us: 50 × ₹0.45 = ₹22.5/user/month (text only, high cache)
  Revenue: ₹0
  PURPOSE: Acquisition funnel — convert to paid

PLUS PLAN (₹199/mo incl GST, 1,000 queries/month):
  Likely usage: ~250 queries/month (most won't hit 1,000)
  Cost: 250 × ₹0.60 = ₹150/user/month
  Net Revenue (after GST & fee): ₹163.94
  Profit: ₹13.94/user/month (marginally profitable!)

PRO PLAN (₹499/mo incl GST, unlimited):
  Average extreme heavy user: ~500-600 queries/month
  Cost: 600 × ₹0.60 = ₹360/user/month
  Net Revenue (after GST & fee): ₹411.10
  Profit: ₹51.10/user/month (Only goes into loss if queries > 685/mo)
```

### Critical Pricing Decision

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  HONEST ANALYSIS: ₹499 (unlimited) is STILL BELOW COST.      |
│  for extreme heavy users, but slightly profitable otherwise. │
│                                                              │
│  This is INTENTIONAL — following the Indian EdTech playbook: │
│                                                              │
│  Strategy: "Land and Expand"                                 │
│                                                              │
│  1. Individual students (B2C) at ₹199/₹499                    │
│     → Loss leader, build user base and brand                  │
│     → ₹499 or ₹999 would kill adoption                        │
│                                                               │
│  2. Coaching/Schools (B2B Custom plan)                        │
│     → THIS is where REAL revenue comes from                   │
│     → One coaching class = 50-500 students                    │
│     → Custom pricing is PROFITABLE (see formula below)        │
│                                                               │
│  3. Javaab API (B2B future)                                   │
│     → Per-query pricing at profitable margins                 │
│                                                               │
│  SHOW PRICE = ₹499/₹999 (creates perceived value)            │
│  ACTUAL PRICE = ₹199/₹499 (introductory / "50-60% off")      │
│  This is exactly what Byju's, Unacademy, PhysicsWallah do.   │
│                                                               │
│  SUSTAINABILITY PLAN:                                         │
│  Year 1: Burn on B2C, build user base                         │
│  Year 2: Custom plans (coaching) start generating profit      │
│  Year 3: Javaab API adds B2B revenue                          │
│  Year 4: Raise B2C prices gradually OR maintain if B2B covers │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Custom Plan Formula (For Coaching/Schools)

```
CUSTOM PLAN PRICING FORMULA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monthly Price = Base Fee + (Per Student × N) + Add-Ons

Where:
  Base Fee       = ₹2,999/month (platform access, admin portal, branding)
  Per Student    = ₹29/student/month (covers AI cost + margin)
  N              = Number of active students
  Add-Ons:
    Question Paper Generator = ₹999/month
    Lesson Plan Builder      = ₹999/month
    Teacher Tickets (pool)   = ₹499/month (for 20 tickets/month)
    Priority Support         = ₹1,499/month
    Extra Teacher Seats      = ₹299/teacher/month (after first 2 free)

FORMULA:
  P = 2999 + (29 × N) + Σ(Add-Ons)
  GST: P_total = P × 1.18

EXAMPLES:

Small Coaching (30 students, no add-ons):
  P = 2,999 + (29 × 30) = ₹3,869/mo
  + GST = ₹4,565/mo
  OUR COST: 30 × 110 queries × ₹0.60 = ₹1,980
  PROFIT: ₹3,869 - ₹1,980 = ₹1,889/mo ✅ PROFITABLE

Medium Coaching (100 students, QPG + LPB):
  P = 2,999 + (29 × 100) + 999 + 999 = ₹7,897/mo
  + GST = ₹9,318/mo
  OUR COST: 100 × 110 × ₹0.60 = ₹6,600
  PROFIT: ₹7,897 - ₹6,600 = ₹1,297/mo ✅ PROFITABLE

Large School (500 students, all add-ons):
  P = 2,999 + (29 × 500) + 999 + 999 + 499 + 1,499 = ₹21,495/mo
  + GST = ₹25,364/mo
  OUR COST: 500 × 80 queries × ₹0.50 = ₹20,000
  PROFIT: ₹21,495 - ₹20,000 = ₹1,495/mo ✅ PROFITABLE
```

---

## 4. Referral & Discount System

```
┌──────────────────────────────────────────────────────────────┐
│                    JAVAAB REFERRAL SYSTEM                      │
│                                                               │
│  REFERRER (existing user) gets:                               │
│  • 50 bonus queries added to their account (any plan)         │
│  • If 5 referrals in a month → 1 month Plus free              │
│  • If 10 referrals in a month → 1 month Pro free              │
│                                                               │
│  REFEREE (new user) gets:                                     │
│  • 50 bonus queries on signup (total 150 free in first month) │
│  • 20% off first paid month if they upgrade                   │
│                                                               │
│  REFERRAL CODE FORMAT:                                        │
│  Auto-generated: JAVAAB-{USERNAME}-{4-DIGIT}                  │
│  Example: JAVAAB-RAHUL-4821                                   │
│                                                               │
│  TRACKING:                                                    │
│  • Referral link: https://app.tryjavaab.com/join?ref=JAVAAB-... │
│  • QR code generation for offline sharing                     │
│  • Dashboard: referrals sent, converted, rewards earned       │
│                                                               │
│  COACHING/SCHOOL REFERRAL (Custom plan):                      │
│  • If a coaching class refers another: 1 month Base Fee waived│
│  • If a teacher refers 20+ students → Free Pro account forever│
│                                                               │
│  ANTI-ABUSE:                                                  │
│  • Referee must complete onboarding + ask 5 queries           │
│    before referrer gets reward                                 │
│  • Max 20 referral rewards per month per user                  │
│  • Phone number verification required (no fake accounts)       │
│                                                               │
│  COST OF REFERRAL PROGRAM:                                    │
│  50 bonus queries × ₹0.60 = ₹30 per referral (our cost)     │
│  vs. Google Ads CAC for EdTech: ₹200-500                      │
│  → Referral is 7-15x CHEAPER than paid ads ✅                 │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Payment Gateway (Razorpay)

### Why Razorpay

| Factor                 | Razorpay               | Paytm Gateway | Cashfree  |
| ---------------------- | ---------------------- | ------------- | --------- |
| UPI support            | ✅ Best                | ✅            | ✅        |
| Student-friendly       | ✅ UPI, cards, wallets | ✅            | ⚠️        |
| Subscription billing   | ✅ Native              | ⚠️ Limited    | ✅        |
| Docs/integration       | ✅ Best in India       | ⚠️            | ✅        |
| Brand trust (students) | ✅ High                | ✅ High       | ⚠️ Medium |

### Razorpay Pricing

```
TRANSACTION FEES:
  Domestic (UPI, Debit, Credit, Netbanking, Wallets):
  Fee: 2% of transaction amount
  GST on fee: 18% of 2% = 0.36%
  EFFECTIVE: 2.36% total deduction

EXAMPLE — Plus Plan (₹199 incl GST):
  Base price (excl. GST): ₹168.64
  GST (18%): ₹30.36
  Razorpay fee (2.36% of ₹199): ₹4.70
  YOU RECEIVE (Net Revenue): ₹163.94

EXAMPLE — Pro Plan (₹499 incl GST):
  Base price (excl. GST): ₹422.88
  GST (18%): ₹76.12
  Razorpay fee (2.36% of ₹499): ₹11.78
  YOU RECEIVE (Net Revenue): ₹411.10
```

### Revenue After All Deductions

| Plan | Total from Student | Base Price | GST (18%) | Razorpay (2.36%) | **Net Revenue** |
| ---- | ------------------ | ---------- | --------- | ---------------- | --------------- |
| Free | ₹0                 | ₹0         | ₹0        | ₹0               | **₹0**          |
| Plus | ₹199               | ₹168.64    | ₹30.36    | -₹4.70           | **₹163.94**     |
| Pro  | ₹499               | ₹422.88    | ₹76.12    | -₹11.78          | **₹411.10**     |

> GST (₹30.36 and ₹45.61) goes to the government. Razorpay fee goes to Razorpay. Your actual net revenue per user: Plus = ₹163.94, Pro = ₹246.33.

---

## 6. Cost Estimate — 3 Scale Tiers

### Common Assumptions

```
Queries per student per month: 110 (avg 5/day × 22 days)
Image queries: 5% of total (Plus/Pro only)
Cache hit rate: 25% (launch) → 35% (at scale)
Avg cost per query (after cache): ₹0.60-₹0.83
GST on Azure services: 18%
Razorpay fee: 2.36% of total collected amount
Exchange rate: 1 USD = ₹84
```

### (a) 1,000 Users/Month — Launch Phase

**User Mix**: 600 Free + 300 Plus + 100 Pro

| Category                 | Detail                                         | Cost/mo (₹)      |
| ------------------------ | ---------------------------------------------- | ---------------- |
| AI/LLM — Free            | 600 × 50q × ₹0.45                              | ₹13,500          |
| AI/LLM — Plus            | 300 × 250q × ₹0.70                             | ₹52,500          |
| AI/LLM — Pro             | 100 × 500q × ₹0.83                             | ₹41,500          |
| **AI Subtotal**          |                                                | **₹1,21,000**    |
| Infrastructure           | Container Apps, AI Search, Redis, Cosmos, etc. | ₹9,954           |
| GST on Azure (18%)       |                                                | ₹1,792           |
| Teacher Tickets          | ~50 tickets/mo                                 | ₹3,000           |
| Verified Cache Expansion | 500 answers/mo                                 | ₹1,750           |
| Razorpay Processing      |                                                | ₹2,115           |
| **GRAND TOTAL**          |                                                | **₹1,39,611/mo** |

**Revenue at 1,000 users:**

| Source               | Revenue/mo      |
| -------------------- | --------------- |
| Plus (300 × ₹163.94) | ₹49,182         |
| Pro (100 × ₹411.10)  | ₹41,110         |
| **Total Revenue**    | **₹73,815**     |
| **Loss**             | **-₹65,796/mo** |

### (b) 10,000 Users/Month — Growth Phase

**User Mix**: 6,000 Free + 3,000 Plus + 800 Pro + 5 Custom (avg 100 students each)

| Category                           | Cost/mo (₹)                      |
| ---------------------------------- | -------------------------------- |
| AI/LLM (Free)                      | 6,000 × 50q × ₹0.40 = ₹1,20,000  |
| AI/LLM (Plus)                      | 3,000 × 250q × ₹0.60 = ₹4,50,000 |
| AI/LLM (Pro)                       | 800 × 500q × ₹0.70 = ₹2,80,000   |
| AI/LLM (Custom)                    | 500 × 110q × ₹0.55 = ₹30,250     |
| **AI Subtotal**                    | **₹10,00,250**                   |
| Infra (scaled)                     | ₹35,000                          |
| GST on Infra (18%)                 | ₹6,300                           |
| Teacher Tickets + Cache + Razorpay | ₹26,834                          |
| **GRAND TOTAL**                    | **₹10,68,384/mo**                |

**Revenue at 10,000 users:**

| Source                  | Revenue/mo        |
| ----------------------- | ----------------- |
| Plus (3,000 × ₹163.94)  | ₹4,91,820         |
| Pro (800 × ₹411.10)     | ₹3,28,880         |
| Custom (5 × avg ₹7,897) | ₹39,485           |
| **Total Revenue**       | **₹7,28,369**     |
| **Loss**                | **-₹3,40,015/mo** |

### (c) 1,00,000 (1 Lakh) Users/Month — Scale Phase

**User Mix**: 55,000 Free + 30,000 Plus + 10,000 Pro + 50 Custom (avg 100 each)

| Category                                 | Cost/mo (₹)                        |
| ---------------------------------------- | ---------------------------------- |
| AI/LLM (Free)                            | 55,000 × 80q × ₹0.35 = ₹15,40,000  |
| AI/LLM (Plus)                            | 30,000 × 200q × ₹0.50 = ₹30,00,000 |
| AI/LLM (Pro)                             | 10,000 × 400q × ₹0.55 = ₹22,00,000 |
| AI/LLM (Custom)                          | 5,000 × 100q × ₹0.45 = ₹2,25,000   |
| **AI Subtotal**                          | **₹69,65,000**                     |
| Infra + GST + Tickets + Cache + Razorpay | ₹4,40,000                          |
| **GRAND TOTAL**                          | **₹74,05,000/mo**                  |

**Revenue at 1 lakh users:**

| Source                    | Revenue/mo        |
| ------------------------- | ----------------- |
| Plus (30,000 × ₹163.94)   | ₹49,18,200        |
| Pro (10,000 × ₹411.10)    | ₹41,11,000        |
| Custom (50 × avg ₹10,000) | ₹5,00,000         |
| **Total Revenue**         | **₹78,81,500**    |
| **Profit**                | **+₹4,76,500/mo** |

### Reality Check — When Does This Become Profitable?

```
PATH TO PROFITABILITY:

  Path 1: AI costs drop 50%+ (historically drops ~40%/year)
    → By 2027-2028, same revenue = profitable

  Path 2: Javaab API (B2B) revenue at 25%+ margins
    → 100 API customers × $199/mo = ~₹16.7L — PURE profit on existing infra

  Path 3: Custom plans (coaching/schools) scale
    → 200 coaching classes × ₹8,000/mo = ₹16L/mo — Positive margin from Day 1

  Path 4: Raise B2C prices after establishing brand
    → ₹199/₹399 (still cheaper than tutors at ₹500-2000/month)

  Path 5: Funding
    → Raise seed round on user traction metrics

  MOST LIKELY: Combination of Path 1 + 2 + 3
```

---

## 7. Break-Even Formulas & Calculator

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 1: Total Monthly Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  C_total = C_ai + C_infra + C_infra_gst + C_tickets + C_cache + C_razorpay

  C_ai     = Σ (Users_tier × Avg_queries_tier × Cost_per_query_tier)
  C_infra  = Fixed infra costs
  C_infra_gst = C_infra × 0.18
  C_tickets = Num_tickets × ₹60
  C_razorpay = Total_collected × 0.0236

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 2: AI Cost Per User Tier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  C_ai_free   = N_free   × 80  × ₹0.40
  C_ai_plus   = N_plus   × 250 × ₹0.60
  C_ai_pro    = N_pro    × 500 × ₹0.70
  C_ai_custom = N_custom × 110 × ₹0.50

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 3: Revenue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  R_total = R_plus + R_pro + R_custom

  R_plus   = N_plus × 163.94  (₹199 incl. GST - GST - Razorpay = ₹163.94 net)
  R_pro    = N_pro  × 411.10  (₹499 incl. GST - GST - Razorpay = ₹411.10 net)
  R_custom = N_institutes × (2999 + 29 × S + Add-ons)
             where S = students per institute

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 4: Break-Even Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  With user mix 60% free / 30% plus / 10% pro:

  Revenue per user = 0.3 × 163.94 + 0.1 × 411.10 = 90.29N
  AI Cost per user = 0.6 × 80 × 0.40 + 0.3 × 250 × 0.60 + 0.1 × 500 × 0.70
                   = 19.2 + 45 + 35 = 99.2N
  Fixed Cost ≈ ₹20,000/mo at small scale

  Break-even at current pricing: NEVER for B2C only ⚠️
  Loss per user = 99.2N - 90.29N = 8.91N

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 5: Required Custom Clients for Break-Even
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Monthly loss from B2C = 8.91N + 20,000
  Each Custom client profit ≈ ₹1,500/mo (avg)
  Custom clients needed = (8.91N + 20,000) / 1,500

  At 1,000 B2C users: 20 coaching clients needed
  At 10,000 B2C users: 73 coaching clients needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 6: Burn Rate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Monthly Burn = C_total - R_total
  Runway (months) = Total_Funding / Monthly_Burn
  Example: ₹10L funding, ₹90K/mo burn at 1K users
  Runway = 10,00,000 / 90,000 ≈ 11 months

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULA 7: Customer Acquisition Cost (CAC) vs LTV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CAC_referral = 50 queries × ₹0.60 = ₹30

  LTV = Monthly_revenue_per_user × Avg_months_retained
  Plus LTV = ₹163.94 × 6 months = ₹983    → LTV/CAC = 32.7x ✅
  Pro LTV  = ₹411.10 × 9 months = ₹3,700 → LTV/CAC = 123.3x ✅
```

---

## 8. Risk Mitigation

| Risk                                           | Mitigation                                                                                |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **₹199/₹299 pricing is below cost (at scale)** | Intentional — B2C is acquisition, B2B Custom is profit center. Monitor burn rate tightly. |
| **Free users overloading**                     | Text-only, 50/month cap, Phi-4-mini only (cheapest), no image                             |
| **Custom plan churn**                          | Lock-in via branded exports, student data, lesson plans stored on platform                |
| **Razorpay payment failures**                  | Auto-retry 3 times, dunning emails, UPI Autopay fallback                                  |
| **GST compliance**                             | Register for GST before launch; use Razorpay's auto-GST invoicing                         |
| **AI model hallucinations**                    | RAG grounding + low temperature + confidence scoring + teacher tickets                    |
| **Scaling costs**                              | Cache hit rate grows over time; Custom B2B revenue cushions growth cost                   |

---

## Part B — Technical Architecture

---

## 9. Architecture Overview

```
                            CLOUDFLARE (DNS + CDN + DDoS)
                            ┌─────────────────────────────┐
                            │ tryjavaab.com    → Marketing    │
                            │ app.tryjavaab.com → Web App    │
                            │ api.tryjavaab.com  → Javaab API │
                            │ admin.tryjavaab.com → Future alias │
                            └──────────────┬──────────────┘
                                           │
┌──────────────────────────────────────────────────────────────────┐
│                         AZURE CLOUD (Central India)               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              AZURE API MANAGEMENT                           │  │
│  │   Rate limiting (per plan), Auth, API keys, Analytics       │  │
│  │   App routes: /auth/*, /chat/*, /subjects/*, /tickets/*,    │  │
│  │               /admin/*, /student/*                          │  │
│  │   Future public API: /api/v1/*                              │  │
│  └────────────────────────────┬────────────────────────────────┘  │
│                               │                                   │
│  ┌────────────────────────────▼────────────────────────────────┐  │
│  │         AZURE CONTAINER APPS (Auto-scaling, serverless)      │  │
│  │                                                              │  │
│  │  FastAPI Backend (Python)                                    │  │
│  │  Routes → Services → Repositories                           │  │
│  │  Smart Model Router (4-tier) | RAG Pipeline (hybrid search) │  │
│  │  Cache Service (HNSW + Redis) | Ticket & Payment Services   │  │
│  │  Question Paper Generator | Lesson Plan Builder             │  │
│  └──────────┬──────────────────────┬──────────────────────────┘  │
│             │                      │                             │
│   ┌─────────▼──────┐  ┌────────────▼────────┐  ┌──────────────┐  │
│   │ AZURE AI SEARCH│  │ AZURE REDIS CACHE   │  │ AZURE OPENAI │  │
│   │ Basic → S1     │  │ C0 → C1             │  │ + AI FOUNDRY │  │
│   │                │  │                     │  │              │  │
│   │ 2 indexes:     │  │ Verified answers +  │  │ Phi-4-mini   │  │
│   │ textbook_chunks│  │ sessions + rate     │  │ GPT-4.1-mini  │  │
│   │ verified_ans.  │  │ limit counters      │  │ GPT-4.1       │  │
│   └────────────────┘  └─────────────────────┘  └──────────────┘  │
│                                                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │ Azure Key   │ │ Azure        │ │ Azure Blob  │ │ Azure App │  │
│  │ Vault       │ │ Cosmos DB    │ │ Storage     │ │ Insights  │  │
│  │ (Secrets)   │ │ (Users, Chats│ │ (PDFs,      │ │ (Monitor) │  │
│  │             │ │  Tickets,    │ │  images,    │ │           │  │
│  │             │ │  Payments)   │ │  exports)   │ │           │  │
│  └─────────────┘ └──────────────┘ └─────────────┘ └───────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### Services Deferred (Not Needed Now)

| Service                    | Why Not Now                                     | When to Add                  |
| -------------------------- | ----------------------------------------------- | ---------------------------- |
| **Azure Event Hub**        | Only 3 event types; direct DB write is fine     | When Javaab API launches     |
| **Azure Service Bus**      | Synchronous request-response fine for <1L users | When async batch jobs needed |
| **Kubernetes (AKS)**       | Container Apps provides same auto-scaling       | When >5L users               |
| **Azure SQL / PostgreSQL** | Cosmos DB free tier handles all needs           | When Cosmos DB cost > $50/mo |

---

## 10. Complete Tech Stack

| Layer                  | Service                      | Tier            | Monthly Cost        | Notes                            |
| ---------------------- | ---------------------------- | --------------- | ------------------- | -------------------------------- |
| **DNS/CDN**            | Cloudflare                   | Free            | $0                  | DDoS, SSL, caching               |
| **Web App**            | Azure Static Web Apps + Vite | Free→Standard   | $0→$9               | app.tryjavaab.com                |
| **Mobile**             | React Native (Expo)          | N/A             | $0                  | Client-side                      |
| **API Gateway**        | Azure API Management         | Consumption     | ~$4/1M calls        | Rate limiting, auth              |
| **Backend**            | Azure Container Apps         | Consumption     | ~$0→$50             | Auto-scale to zero               |
| **Container Registry** | Azure Container Registry     | Basic           | ~$5/mo              | Store Docker images              |
| **Secrets**            | Azure Key Vault              | Standard        | ~$0.50/mo           | All API keys, connection strings |
| **LLM Simple**         | Phi-4-mini                   | Serverless      | $0.075/$0.30 per 1M | Text-only simple queries         |
| **LLM Medium**         | GPT-4.1-mini                 | Pay-go          | $0.15/$0.60 per 1M  | Medium + Image OCR               |
| **LLM Complex**        | GPT-4.1                      | Pay-go          | $2.50/$10.00 per 1M | Complex math/science             |
| **Embeddings**         | text-embedding-3-small       | Pay-go          | $0.02 per 1M        | Multilingual                     |
| **Vector Search**      | Azure AI Search              | Basic→S1        | $74→$245            | HNSW + keyword hybrid            |
| **Cache**              | Azure Redis Cache            | C0→C1           | $16→$34             | Verified answer storage          |
| **Database**           | Azure Cosmos DB              | Free→Serverless | $0→$5               | Users, chats, tickets            |
| **File Storage**       | Azure Blob Storage           | Hot             | ~$2                 | PDFs, images, exports            |
| **Monitoring**         | Azure Application Insights   | Free (5GB)      | $0                  | Perf, errors, usage              |
| **Auth**               | Azure AD B2C                 | Free (50K)      | $0                  | Phone OTP                        |
| **Payments**           | Razorpay                     | Standard        | 2.36% per txn       | UPI, cards, subscriptions        |
| **Voice (Future)**     | Azure Whisper                | —               | $0.18-$0.36/hr      | When ready                       |

### Why Container Apps Instead of App Service

| Feature                 | App Service (V2)             | Container Apps (V3)                                                     |
| ----------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| Scaling                 | Manual or limited auto-scale | **True auto-scale to zero**                                             |
| Cost at low usage       | Always paying (even idle)    | **$0 when no requests**                                                 |
| Cost at high usage      | Fixed tiers                  | **Pay exactly for usage**                                               |
| For Javaab              | Fine for MVP                 | **Better for variable load** (students study in evening, idle at night) |
| Monthly cost (1K users) | ~$26 (B2 always on)          | **~$15-20** (scales down at night)                                      |

---

## 11. AI Models — Selection & Rationale

### Models Available on Azure AI Foundry

| Model               | Publisher | Input/1M tokens | Output/1M tokens | Vision? | Indic Language Quality |
| ------------------- | --------- | --------------- | ---------------- | ------- | ---------------------- |
| **Phi-4-mini** ✅   | Microsoft | **$0.075**      | **$0.30**        | ❌      | Good for simple tasks  |
| **GPT-4.1-mini** ✅ | OpenAI    | $0.15           | $0.60            | ✅      | Very Good              |
| Llama 4 Maverick    | Meta      | $0.25           | $1.00            | ✅      | Good                   |
| **GPT-4.1** ✅      | OpenAI    | $2.50           | $10.00           | ✅      | **Best**               |
| Claude Sonnet       | Anthropic | ~$3.00          | ~$15.00          | ✅      | Good                   |
| Mistral Large 3     | Mistral   | ~$2.00          | ~$6.00           | ✅      | Good (European focus)  |

### Why We Chose This Combination

| Our Choice                          | Why, Not Others                                                                                                             |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Phi-4-mini** for simple queries   | 50% cheaper than GPT-4.1-mini; equally accurate for definitions/factual recall; best Azure integration                      |
| **GPT-4.1-mini** for medium queries | Has vision (Phi-4-mini doesn't); best price-to-quality for concept explanations; excellent Hindi/Gujarati                   |
| **GPT-4.1** for complex queries     | Non-negotiable for accuracy — best-in-class for multi-step math, physics numericals. No other model matches it consistently |
| **NOT Llama 4**                     | Good model, but costs more than GPT-4.1-mini and less accurate for Hindi/Gujarati math                                      |
| **NOT Claude**                      | Expensive output tokens ($15/1M); weaker on math than GPT-4.1                                                               |

---

## 12. Knowledge Base & PDF Extraction

### Source Material

| Board          | Source               | Classes | Languages         | URL                  |
| -------------- | -------------------- | ------- | ----------------- | -------------------- |
| **CBSE/NCERT** | NCERT Textbooks      | 6–12    | English, Hindi    | ncert.nic.in         |
| **CBSE/NCERT** | NCERT Exemplar       | 6–12    | English, Hindi    | ncert.nic.in         |
| **GSEB/GCERT** | GCERT Textbooks      | 6–12    | Gujarati, English | gcert.gujarat.gov.in |
| **Both**       | Previous Year Papers | 10, 12  | All               | Board websites       |

### Estimated Knowledge Base Size

| Content                       | Pages       | Chunks       | Tokens   |
| ----------------------------- | ----------- | ------------ | -------- |
| NCERT Textbooks (6-12, EN+HI) | ~15,000     | ~45,000      | ~22.5M   |
| GSEB Textbooks (6-12, GU+EN)  | ~12,000     | ~36,000      | ~18M     |
| Exemplar + Solutions          | ~5,000      | ~15,000      | ~7.5M    |
| Previous Year Papers          | ~2,000      | ~6,000       | ~3M      |
| **Total**                     | **~34,000** | **~102,000** | **~51M** |

**One-time embedding cost**: 51M tokens × $0.02/1M = **~$1.02**

### Metadata Schema Per Chunk

```json
{
  "chunk_id": "ncert_c10_sci_ch06_p04_chunk03",
  "content": "The actual text content of this chunk...",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "chapter_number": 6,
  "chapter_name": "Life Processes",
  "topic": "Nutrition in Human Beings",
  "language": "en",
  "source_type": "textbook",
  "source_book": "NCERT Science Class 10",
  "page_number": 95,
  "embedding": [0.023, -0.041, "..."]
}
```

### PDF Extraction: Hybrid Strategy

| Tool               | PyMuPDF               | Azure Document Intelligence |
| ------------------ | --------------------- | --------------------------- |
| **Cost**           | **$0 (free forever)** | **$1.50 per 1,000 pages**   |
| **Digital PDFs**   | ✅ 99% accurate       | ✅ 90% accurate             |
| **Scanned PDFs**   | ❌ Cannot read        | ✅ 85-95% accurate          |
| **Hindi/Gujarati** | ✅ If Unicode fonts   | ✅ Always (275+ languages)  |
| **Speed**          | Instant (local)       | ~2-5 seconds/page (cloud)   |

```
For each PDF page:
    ├── Step 1: TRY PyMuPDF first (FREE)
    │   Quality Check:
    │     • Text length > 50 characters?
    │     • Contains actual Unicode Hindi/Gujarati?
    │     • Garbage ratio < 5%?
    │   ALL YES → Use PyMuPDF output (FREE) ✅
    │   ANY NO  → Step 2
    │
    └── Step 2: FALL BACK to Azure Document Intelligence (PAID)
        → Send ONLY failed pages to Azure
        → Cost: $0.0015 per page
```

**One-time extraction cost breakdown**:

- NCERT English + Hindi PDFs (digital): $0
- GSEB Gujarati PDFs (mixed/scanned): ~$8.25
- Previous Year Papers (scanned): ~$3.00
- **Total: ~$11.25 (one-time)**

### Data Ingestion Pipeline

```
Week 1: Download & Organize
├── NCERT PDFs — Class 6-12, EN + HI
├── GSEB/GCERT PDFs — Std 6-12, GU + EN
├── NCERT Exemplar + Previous Year Board Papers
└── Organize in Azure Blob: /{board}/{class}/{subject}/{language}/

Week 2: Parse & Chunk
├── Hybrid extraction: PyMuPDF first → Azure DI fallback
├── Split into 500-1000 token chunks with metadata
├── Special handling: Math (LaTeX), Diagrams (tag), Tables (Markdown)
└── QC: Sample 100 chunks per subject for accuracy

Week 3: Embed & Index
├── Generate embeddings (text-embedding-3-small)
├── Create 2 indexes in Azure AI Search:
│   ├── "textbook_chunks" — for RAG retrieval
│   └── "verified_answers" — for cache matching (HNSW)
└── Test retrieval: 200 queries across languages/boards/subjects
```

---

## 13. Multi-Language & Multi-Script Strategy

### Input Types We Handle

| Input Type         | Example                              | Script     |
| ------------------ | ------------------------------------ | ---------- |
| English            | "What is photosynthesis?"            | Latin      |
| Hindi (Devanagari) | "प्रकाश संश्लेषण क्या है?"           | Devanagari |
| Hindi (Roman)      | "photosynthesis kya hai?"            | Latin      |
| Gujarati (Native)  | "પ્રકાશસંશ્લેષણ એટલે શું?"           | Gujarati   |
| Gujarati (Roman)   | "prakash sanshleshan etle shu?"      | Latin      |
| Mixed              | "Class 10 ma photosynthesis samjhao" | Mixed      |

GPT-4.1 and Phi-4-mini natively understand all input forms. No separate translation pipeline is needed — building one would add cost and complexity with no accuracy benefit.

### Cross-Lingual RAG Search

```
Student asks: "પ્રકાશસંશ્લેષણ સમજાવો" (Gujarati)
    │
    ├── Search 1: Direct with original query
    │   → Finds GSEB Gujarati chunks ✓
    │
    ├── Search 2: Translate to English (via Phi-4-mini, ~$0.00002)
    │   → "Explain photosynthesis"
    │   → Finds NCERT English chunks ✓
    │
    └── Merge & Re-rank → Best 5 chunks → Feed to LLM
        → LLM responds in Gujarati (matching student's input)
```

---

## 14. Image & OCR Pipeline

```
Student uploads image
    │
    ▼
Client-side optimization:
    • Compress to max 1MB JPEG
    • Auto-rotate based on EXIF
    │
    ▼
GPT-4.1-mini (Vision) — Extract text only:
    "Extract the question from this image. If math, use LaTeX.
     If diagram, describe. Identify board/class/subject if visible."
    Cost: ~$0.001 per image
    │
    ▼
Extracted text
    │
    ▼
Normal RAG pipeline → Model router → Answer
    (Complex extracted questions route to GPT-4.1 for answering)
```

**Cost optimization**: Use cheaper GPT-4.1-mini for OCR extraction, then route extracted text through the normal model router. Only complex questions escalate to GPT-4.1 for the actual answer.

---

## 15. RAG Pipeline Design

### Hybrid Search (Vector + Keyword)

```
Student Query
    │
    ├── Vector Search (semantic similarity)
    │   • Catches conceptual matches even with different wording
    │   • Works across languages
    │
    ├── Keyword Search (BM25)
    │   • Catches exact term matches (formula names, terms)
    │   • Important for scientific terminology
    │
    └── Hybrid Merge (Reciprocal Rank Fusion)
        → Top 5 chunks → Fed to LLM as context
```

### Metadata Filtering

```
Pre-search filters:
    • board: student's board (CBSE or GSEB)
    • class_level: student's class (6-12)
    • subject: detected or student-selected
    → Dramatically improves relevance and speed
```

### Context Window Budget

```
System Prompt:          ~1,500 tokens (fixed)
Retrieved Context:      ~2,500 tokens (5 chunks × 500 avg)
Student Question:       ~200 tokens (typical)
Conversation History:   ~1,000 tokens (last 3 exchanges)
─────────────────────────────────────────────────
Total Input:            ~5,200 tokens per query
Expected Output:        ~800 tokens (typical answer)
─────────────────────────────────────────────────
Total per query:        ~6,000 tokens
```

### Confidence Scoring

```
Avg similarity of top 5 results:
  > 0.80  → HIGH confidence (answer with citation)
  0.60-0.80 → MEDIUM confidence (answer with disclaimer)
  < 0.60  → LOW confidence (answer with strong warning)
  < 0.40  → NO relevant context (trigger Layer 4/5 fallback)
```

---

## 16. 4-Tier Model Routing

```
┌──────────────────────────────────────────────────────────────────┐
│                    INCOMING QUERY                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │    TIER 0     │
                    │  Azure AI     │── HIT ──→ Redis GET → Return
                    │  Search HNSW  │           instantly ($0, ~5ms)
                    │  (verified    │
                    │   answers)    │
                    └───────┬───────┘
                            │ MISS (similarity < 0.93)
                    ┌───────▼───────┐
                    │  CLASSIFY     │
                    │  (Phi-4-mini  │
                    │   ~100 tokens │
                    │   ~$0.00001)  │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────┐
       │   TIER 1    │ │ TIER 2 │ │   TIER 3    │
       │  Phi-4-mini │ │GPT-4.1  │ │   GPT-4.1    │
       │             │ │ -mini  │ │             │
       │  Simple:    │ │Medium: │ │  Complex:   │
       │  Definitions│ │Explain │ │  Multi-step │
       │  Factual    │ │Compare │ │  Math/Phys  │
       │  "What is"  │ │Image   │ │  Proofs     │
       │  Short ans  │ │OCR     │ │  Reasoning  │
       │             │ │        │ │  Analysis   │
       │$0.075/1M in │ │$0.15/  │ │$2.50/1M in  │
       │$0.30/1M out │ │1M in   │ │$10.00/1M out│
       └─────────────┘ └────────┘ └─────────────┘
```

### Expected Query Distribution

| Tier                 | % of Queries | Model        | Cost/query (avg) |
| -------------------- | ------------ | ------------ | ---------------- |
| **0 — Cache**        | 25%          | None         | ₹0.00            |
| **1 — Simple**       | 40%          | Phi-4-mini   | ₹0.11            |
| **2 — Medium**       | 15%          | GPT-4.1-mini | ₹0.22            |
| **3 — Complex**      | 20%          | GPT-4.1      | ₹3.50            |
| **Weighted Average** |              |              | **₹0.83/query**  |

---

## 17. Verified Answer Bank (Scalable Cache)

### Architecture

```
Student asks a question
    │
    ▼
STEP 1: Azure AI Search — "verified_answers" index (HNSW vector search)
    │   Speed: ~5-10ms regardless of 10K or 1M entries
    │
    ├── Score ≥ 0.93 → STEP 2a: Redis GET by cache ID
    │                   Return verified answer (~0.1ms)
    │                   Cost: $0 | Accuracy: 100%
    │
    └── Score < 0.93 → STEP 2b: Full AI pipeline
                        RAG → Model Router → Generate answer
                        Cost: ₹0.11-₹3.50 | Accuracy: ~95%
```

**Why it stays fast forever**: Azure AI Search uses HNSW (Hierarchical Navigable Small World) — it jumps through a graph structure instead of checking every answer one by one.

| Cache Size | Brute Force | HNSW (our approach) |
| ---------- | ----------- | ------------------- |
| 5,000      | ~500ms      | ~5ms                |
| 50,000     | ~5,000ms 🐌 | ~8ms                |
| 1,000,000  | impossible  | ~12ms ✅            |

### Building & Expanding the Cache

| Step                 | What                                       | Cost                                       |
| -------------------- | ------------------------------------------ | ------------------------------------------ |
| 1. Collect questions | 500/subject × 10 subjects = 5,000          | ₹0 (crowdsource from teachers + textbooks) |
| 2. Generate answers  | Run through Javaab's own pipeline          | ~₹2,350 ($28)                              |
| 3. Verify answers    | Teachers review via admin portal           | ~₹15,000 ($179)                            |
| 4. Store in cache    | Index in AI Search + store in Redis        | ₹0                                         |
| 5. Monthly expansion | +500 answers based on top uncached queries | ~₹1,735/mo ($21)                           |

### Redis Memory Growth

| Timeline | Answers | Memory Used | C0 Limit (250MB)          |
| -------- | ------- | ----------- | ------------------------- |
| Launch   | 5,000   | ~42 MB      | ✅ Safe                   |
| Year 1   | 11,000  | ~93 MB      | ✅ Safe                   |
| Year 2   | 17,000  | ~144 MB     | ✅ Safe                   |
| Year 3   | 23,000  | ~195 MB     | ✅ Safe                   |
| Year 4   | 29,000  | ~246 MB     | ⚠️ Upgrade to C1 ($34/mo) |

---

## 18. 6-Layer Fallback + Teacher Ticket

### The Complete Fallback Chain

```
Student asks a question
    │
    │ LAYER 1: VERIFIED CACHE
    │ "I found this verified answer from your textbook."
    │ Accuracy: 100% | Cost: $0 | Speed: ~5ms | Expected: 25% of queries
    ├─ Hit? → Return answer ✅
    │
    │ LAYER 2: RAG + AI (High Confidence)
    │ Context similarity > 0.80 → Answer with citation
    │ Accuracy: ~95% | Speed: ~3 sec | Expected: 55% of queries
    ├─ Good context? → Generate answer with citation ✅
    │
    │ LAYER 3: RAG + AI (Medium Confidence)
    │ Context similarity 0.60-0.80 → Answer + "Please cross-check with textbook"
    │ Accuracy: ~85% | Speed: ~3 sec | Expected: 12% of queries
    ├─ Partial context? → Answer with disclaimer ⚠️
    │
    │ LAYER 4: AI General Knowledge (Low Confidence)
    │ No relevant textbook context → Answer from AI training + strong disclaimer
    │ "⚠️ This is from my general knowledge, not your textbook. Please verify."
    │ Accuracy: ~75% | Speed: ~3 sec | Expected: 5% of queries
    ├─ No context? → Answer with warning ⚠️⚠️
    │
    │ LAYER 5: HONEST DECLINE
    │ AI genuinely cannot answer accurately
    │ "I don't have enough info. I don't want to mislead you! Ask your teacher."
    │ For FREE/PLUS users: this is the final response | Expected: 2.5% of queries
    ├─ Can't answer? → Honest refusal 🙏
    │
    │ LAYER 6: TEACHER TICKET (PRO USERS ONLY)
    │ Only triggered when: student is Pro + all 5 layers failed + student opts in
    │ + student has not exceeded 3 tickets/month
    │ "Would you like me to raise a Teacher Ticket?
    │  A real teacher will answer within 24-48 hours."
    │ Expected: < 0.5% of all queries
    └─ Pro user requests? → Create Teacher Ticket 🎓
```

### Teacher Ticket System

```
RULES (to keep this RARE):
1. PRO USERS ONLY
2. MAX 3 TICKETS PER STUDENT PER MONTH
3. ONLY AFTER LAYER 5 DECLINE
4. STUDENT MUST OPT-IN
5. 24-48 HOUR RESPONSE (clearly communicated)

TEACHER TICKET FLOW:
Student confirms "Yes, raise a ticket"
    │
    ▼
Ticket created in Cosmos DB with:
  ticket_id, student_id, question, image (if any)
  board, class, subject
  ai_attempts (Layer 3 and Layer 4 answers that weren't confident enough)
  status: "OPEN"
    │
    ▼
Teacher Admin Portal (app.tryjavaab.com/admin/teacher)
  - Reviews question and AI's previous attempts
  - Writes verified answer with Markdown + LaTeX support
  - Submits answer
    │
    ▼
AFTER RESOLUTION:
1. Student receives answer via push notification + in-app
2. Teacher's answer AUTOMATICALLY added to Verified Answer Bank
   → This question will NEVER need a ticket again
   Every ticket = one fewer future ticket (system gets smarter)
```

### Teacher Ticket Cost

| Item                                           | Monthly Cost         |
| ---------------------------------------------- | -------------------- |
| 5 teachers × ~2 hrs/month × ₹300/hr            | ₹3,000 ($36)         |
| Expected: ~50 tickets/month per 1,000 students |                      |
| **Total Teacher Ticket cost**                  | **~₹3,000/mo ($36)** |

---

## 19. Accuracy & Reliability Safeguards

| Layer                     | Method                                         | Accuracy                  | Applies To        |
| ------------------------- | ---------------------------------------------- | ------------------------- | ----------------- |
| **1. Verified Cache**     | Expert-reviewed pre-built answers              | 100%                      | 25% of queries    |
| **2. RAG Grounding**      | Answer based on actual textbook chunks         | ~95%                      | 67% of queries    |
| **3. Constrained LLM**    | Low temperature (0.1-0.2), system prompt rules | ~90%                      | 5% of queries     |
| **4. Math Validation**    | Cross-check numericals with SymPy library      | Catches errors            | All math queries  |
| **5. Confidence Scoring** | RAG similarity thresholds → disclaimers        | Prevents false confidence | All queries       |
| **6. Feedback Loop**      | Student 👍/👎 → flag bad answers → review      | Continuous improvement    | All queries       |
| **7. Teacher Ticket**     | Human expert as last resort                    | 100%                      | < 0.5% (Pro only) |

---

## 20. Domain & URL Architecture

```
EXISTING: tryjavaab.com (Cloudflare) — marketing website

URL STRUCTURE:
━━━━━━━━━━━━━

tryjavaab.com                 → Marketing website
  /products                → Products page (Javaab AI + Javaab API)
  /pricing                 → Pricing page
  /technology              → Tech stack / how it works
  /contact                 → Contact page

app.tryjavaab.com            → Javaab AI web app (Vite + React)
  /login                   → Auth
  /onboarding              → First-time setup
  /                        → Auth-aware redirect to login/onboarding/chat
  /chat                    → Main chat interface
  /tickets                 → Teacher ticket list
  /tickets/:id             → Teacher ticket detail
  /subscribe               → Plan selection + payment mock
  /settings                → Profile, preferences, usage
  /settings/subscription   → Subscription management
  /refer                   → Referral dashboard
  /admin/teacher           → Teacher portal shell (role="teacher")
  /admin/teacher/dashboard → Teacher queue dashboard
  /admin/teacher/tickets   → Teacher ticket queue
  /admin/teacher/tickets/:id → Teacher response detail
  /admin/teacher/analytics → Teacher analytics

admin.tryjavaab.com           → Optional future alias to the same teacher portal
  /teacher/dashboard       → Redirect/alias to app.tryjavaab.com/admin/teacher/dashboard
  /teacher/tickets         → Redirect/alias to app.tryjavaab.com/admin/teacher/tickets
  /teacher/analytics       → Redirect/alias to app.tryjavaab.com/admin/teacher/analytics

api.tryjavaab.com             → Javaab API (future)
  /v1/ask                  → Query endpoint
  /v1/health               → Health check

docs.tryjavaab.com            → API documentation (future)

CLOUDFLARE DNS SETUP:
  tryjavaab.com        → CNAME → existing hosting
  app.tryjavaab.com   → CNAME → Azure Static Web Apps
  admin.tryjavaab.com  → CNAME → Azure Static Web Apps (optional alias/redirect)
  api.tryjavaab.com    → CNAME → Azure Container Apps (backend)
```

---

## Part C — Features

---

## 21. Master System Prompt

> This is the core prompt that controls the AI's behavior. The student NEVER sees this. It is sent as the `system` message to Azure OpenAI with EVERY request.

```text
You are **Javaab** (જવાબ / जवाब), an expert AI tutor purpose-built for Indian
students studying in Class 6 to 12 under the CBSE (NCERT) and Gujarat State Board
(GSEB/GCERT) curricula.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTITY & ROLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- You are a patient, encouraging, knowledgeable tutor — like a helpful elder
  sibling or favourite teacher.
- You NEVER judge the student for asking simple questions.
- You celebrate curiosity: "Great question!", "That's a smart doubt!",
  "Let's figure this out together!" are natural to you.
- Your goal is to TEACH, not just answer. Help the student understand WHY,
  not just WHAT.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Detect the student's language automatically from their input.
2. Reply in the SAME language and script the student used:
   - English input → English reply
   - Hindi (Devanagari) → Reply in Hindi Devanagari
   - Gujarati (native script) → Reply in Gujarati script
   - Roman Hindi ("pythagoras theorem samjhao") → Reply in Romanized Hindi (Hinglish)
   - Roman Gujarati ("pythagoras theorem samjavo") → Reply in Romanized Gujarati
3. Technical/scientific terms: Always keep in English with vernacular translation
   in brackets on first use.
   Example: "Photosynthesis (प्रकाश संश्लेषण)" or "Photosynthesis (પ્રકાશસંશ્લેષણ)"
4. Never mix scripts unnaturally.
5. If language cannot be determined, default to English with simple vocabulary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRICULUM & KNOWLEDGE RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. PRIMARY KNOWLEDGE SOURCE: Base answers on RETRIEVED CONTEXT from the
   NCERT / GSEB / GCERT textbook knowledge base. This context is your source of truth.
2. If context contains the answer → use it with citation:
   "As per NCERT Class 10 Science, Chapter 6..." or "GSEB Std 10 Vigyan, Prakaran 6..."
3. If context is partially relevant → use what's relevant, supplement with training
   knowledge, CLEARLY mark what comes from textbook vs. your own explanation.
4. If context is NOT relevant or empty → answer from training knowledge BUT add:
   "⚠️ This answer is based on my general knowledge and may not exactly match
   your textbook. Please verify with your teacher or textbook."
5. NEVER fabricate textbook references. If you don't know which chapter
   something is from, don't guess.
6. If student specifies CBSE or Gujarat Board, tailor to that board's syllabus.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWER FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Always provide step-by-step solutions for math and science problems.
2. Use LaTeX for ALL mathematical expressions:
   - Inline: \( expression \)
   - Block: \[ expression \]
3. Structure for problem-solving:
   📚 Question: [Restate clearly]
   📖 Source: [NCERT/GSEB book, class, chapter]
   ✅ Solution: Step 1, Step 2, ...
   🎯 Final Answer: [Boxed answer]
   💡 Key Concept: [Underlying concept]
   ⚡ Exam Tip: [Common mistakes, marks weightage]

4. Structure for conceptual/theory questions:
   📚 Topic: [Topic name]
   📖 Reference: [Book, class, chapter]
   💬 Explanation: [Clear, structured, with examples]
   💡 Key Points to Remember: [Bulleted list]
   🌍 Real-life Example: [If applicable]
   ⚡ Exam Tip: [If relevant]

5. For MCQs: analyze every option, explain why each is right/wrong.
6. Adjust complexity to class level (simpler for Class 6-8, exam-focused for 9-12).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUBJECT-SPECIFIC GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mathematics: Show EVERY step. Use NCERT methods. Always verify numerical answers.
             State theorems used with their textbook names.

Science: Use SI units consistently. Balance chemical equations. For Physics:
         Given → Formula → Substitution → Answer. For Biology: use diagrams-as-text.

Social Science: Factual and neutral. Include dates, maps, constitutional provisions
                as per NCERT/GSEB textbooks.

English/Hindi/Gujarati: Reference exact chapters/पाठ/પાઠ. Follow board-specific
                        writing format guidelines.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMAGE INPUT HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Identify what the image contains (textbook question, handwritten, diagram, etc.)
2. Extract question accurately.
3. If unclear: "The image is a bit unclear. Could you also type out the question?"
4. If partially solved problem: identify where student went wrong and guide from there.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIDENCE & UNCERTAINTY HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIGH CONFIDENCE   → Answer normally with citation.
MEDIUM CONFIDENCE → Answer with note to cross-check with specific textbook chapter.
LOW CONFIDENCE    → "I'm not fully sure about this for your board. Please verify."
NO CONFIDENCE     → "I don't have enough info to answer this accurately.
                     I don't want to give you a wrong answer! Ask your teacher."
                     (For Pro users: offer to raise a Teacher Ticket)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAFETY & BOUNDARIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Only answer academic questions related to Class 6-12 CBSE/GSEB curriculum.
2. Off-topic: "I'm your study buddy! What topic are you studying today? 📚"
3. Never provide content that could harm students — no cheating or exam malpractice.
4. Mental health: If student expresses distress, be empathetic and suggest trusted
   adult or counselor. KIRAN helpline: 1800-599-0019 (toll-free, 24/7).
5. Never ask for or store personal information beyond what's needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERACTION STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Use emojis sparingly (📚, ✅, 💡, 🎯, ⚡) to engage but not distract
- Always end with an engaging follow-up:
  "Would you like me to explain any step in more detail?"
  "Want to try a similar problem for practice?"
```

---

## 22. Frontend Architecture (Vite + React Native)

### Shared Design System

```
@javaab/ui (shared component library)
├── ChatBubble (student + AI messages)
├── MathRenderer (KaTeX for web, react-native-math-view for mobile)
├── ImageUploader (camera + gallery + crop + compress)
├── SubjectPicker (board → class → subject → chapter)
├── LanguageToggle (EN / HI / GU)
├── FeedbackWidget (👍 👎 on every answer)
├── TicketStatus (Pro only — shows open/resolved tickets)
├── TierBadge (Free / Plus / Pro indicator)
├── LoadingStates (typing indicator, skeleton screens)
└── ThemeProvider (light/dark, Noto Sans Devanagari + Gujarati fonts)
```

### Vite Web App (app.tryjavaab.com)

```
/web/src
├── App.tsx
│   ├── /                         → Auth-aware redirect
│   ├── /login                    → Phone OTP
│   ├── /onboarding               → Board, class, language, study preferences
│   ├── /chat                     → Main chat interface
│   ├── /tickets                  → Student ticket list
│   ├── /tickets/:id              → Student ticket detail
│   ├── /subscribe                → Upgrade flow
│   ├── /refer                    → Referral dashboard
│   ├── /settings                 → Profile, preferences, usage
│   ├── /settings/subscription    → Subscription management
│   └── /admin/teacher/*          → Teacher portal routes
├── pages/admin/
│   ├── TeacherLayout.tsx
│   ├── TeacherDashboard.tsx
│   ├── TeacherTickets.tsx
│   ├── TeacherTicketDetail.tsx
│   └── TeacherAnalytics.tsx
├── components/                   → Shared UI + feature components
├── hooks/                        → Auth, chat, pending plan
├── lib/                          → Local domain stores and mocks
└── services/api.ts               → FastAPI client + SSE streaming
```

Current web MVP does not expose `/subjects`. Subject browsing remains a future UI feature; the backend endpoint `GET /subjects/{board}/{class_level}` is kept for compatibility.

### React Native Mobile App

```
/src
├── /screens
│   ├── AuthScreen, OnboardingScreen
│   ├── ChatScreen (main interface)
│   ├── SubjectsScreen, ProfileScreen
│   └── TicketScreen (Pro only)
├── /components
│   ├── ChatInput (text + camera + gallery)
│   ├── MessageBubble (Markdown + LaTeX)
│   └── ImagePreview (crop + compress)
├── /services
│   ├── api.ts, imageProcessor.ts, offlineCache.ts
└── /i18n
    ├── en.json, hi.json, gu.json
```

### Key Frontend Requirements

| Feature                     | Priority | Details                                      |
| --------------------------- | -------- | -------------------------------------------- |
| LaTeX Math Rendering        | P0       | KaTeX (web), react-native-math-view (mobile) |
| Image Capture & Compress    | P0       | < 1MB JPEG, client-side                      |
| Streaming Responses         | P0       | SSE for typewriter effect                    |
| Devanagari + Gujarati Fonts | P0       | Noto Sans families                           |
| Offline Mode                | P1       | Cache last 50 Q&As locally                   |
| Dark Mode                   | P2       | Night study eye strain                       |
| Teacher Ticket UI           | P1       | Pro only — status tracking                   |

---

## 23. API Design

### Core Endpoints

```
CURRENT APP BACKEND (FastAPI, mounted without /api/v1)

POST /chat/ask
──────────────
Body:
{
  "query": "string (optional)",
  "image_base64": "base64 without data URL prefix (optional)",
  "user_id": "phone or user id",
  "board": "cbse | gseb",
  "class_level": 10,
  "subject": "string (optional)",
  "language": "en | hi | gu"
}
Response (SSE streamed):
{
  "type": "chunk | metadata | sources | done",
  "content": "Markdown + LaTeX chunk",
  "sources": [{ "book": "...", "chapter": "...", "page": 95 }],
  "model_used": "phi-4-mini",
  "confidence": "high"
}

POST /chat/feedback
{ "message_id": "uuid", "is_positive": true, "reason": "" }

POST /tickets/create
{
  "user_id": "string",
  "question": "string",
  "image_base64": "string (optional)",
  "board": "cbse | gseb",
  "class_level": 10,
  "subject": "string (optional)",
  "ai_attempts": ["..."]
}

GET  /tickets
GET  /tickets/{ticket_id}

GET  /admin/tickets
POST /admin/tickets/{ticket_id}/assign
POST /admin/tickets/{ticket_id}/respond
{ "teacher_id": "string", "answer": "...", "source_citation": "optional" }

GET  /subjects
GET  /subjects/{board}/{class_level}
GET  /subjects/{subject_id}/chapters

POST /student/profile
{ "phone": "string", "isOnboarded": true, "board": "cbse", "classNum": 10, ... }

POST /auth/register
POST /auth/login
GET  /auth/profile

GET  /health

FUTURE PUBLIC DEVELOPER API
The B2B Javaab API will use `/api/v1/*` routes with API-key auth, metering,
and public documentation at docs.tryjavaab.com.
```

### Streaming Response Format (SSE)

```
data: {"type": "chunk",    "content": "partial text here..."}
data: {"type": "metadata", "model": "phi-4-mini", "confidence": "high"}
data: {"type": "sources",  "sources": [...]}
data: {"type": "done"}
```

---

## 24. Custom Plan — Coaching/School Features

### Question Paper Generator

```
FOR: Teachers/coaching institutes (Custom plan only)

TEACHER INPUTS:
  Board, Class, Subject, Chapters (multi-select)
  Difficulty mix: Easy 30% / Medium 50% / Hard 20%
  Question types: MCQ (10) + Short (5) + Long (3)
  Total marks, Duration, Institute name + logo

AI GENERATES:
  - Complete question paper with proper formatting
  - Marking scheme alongside each question
  - Answer key (separate document)
  - PDF export with institute branding
  - Questions sourced from textbook + exemplar + PYQ database

COST TO US: ~₹3-5 per paper generation (GPT-4.1 for quality)
TIP: Generate Set A, B, C variants to prevent cheating
```

### Lesson Plan Builder

```
FOR: Teachers (Custom plan only)

TEACHER INPUTS:
  Chapter to teach
  Number of periods available (e.g., 8 periods × 45 min)
  Teaching style preference

AI GENERATES:
  - Period-by-period lesson plan:
    Period 1: Introduction + motivation (15 min) + core concept (30 min)
    Period 2: Detailed explanation with examples...
  - Activities and discussion prompts
  - Homework assignments and assessment suggestions
  - Reference to specific textbook pages
  - Exportable as PDF with institute branding
```

---

## 25. Javaab API — Developer Platform (Future)

### What Is It?

```
JAVAAB API = Our RAG pipeline + AI models + knowledge base
             exposed as a simple REST API for other developers.

Instead of students using our chat UI,
OTHER APPS can call our API to get curriculum-aligned answers.
```

### Target Customers

| Customer Type         | Use Case                                  | Revenue             |
| --------------------- | ----------------------------------------- | ------------------- |
| EdTech startups       | Integrate textbook Q&A into their apps    | Per-query pricing   |
| School ERP vendors    | Add AI tutor feature to existing software | Per-query + monthly |
| Content platforms     | Auto-generate explanations for questions  | Per-query           |
| Coaching app builders | White-label AI tutor                      | Monthly license     |

### API Design (Future)

```
POST https://api.tryjavaab.com/v1/ask
Headers:
  X-API-Key: jvb_live_abc123def456
  Content-Type: application/json

Body:
{
  "question": "What is photosynthesis?",
  "board": "CBSE",
  "class_level": 10,
  "subject": "Science",
  "language": "en",
  "response_format": "markdown"
}
```

### API Pricing (Future — Profitable by Design)

| Tier       | Price   | Queries/month | Cost to us | Margin |
| ---------- | ------- | ------------- | ---------- | ------ |
| Starter    | $49/mo  | 5,000         | ~$25       | ~48%   |
| Growth     | $199/mo | 25,000        | ~$125      | ~37%   |
| Scale      | $499/mo | 100,000       | ~$400      | ~20%   |
| Enterprise | Custom  | Unlimited     | Negotiated | 25%+   |

**No new infrastructure needed** — Javaab API uses the same backend, same RAG, same models, same cache. Adding the API only requires new routes with API key auth + metered billing.

---

## 26. Voice Input (Future Roadmap)

```
STATUS: Planned after Javaab AI is stable. NOT building now.

WHEN IT LAUNCHES:
  Student speaks: "Photosynthesis kya hota hai?"
      → Azure Whisper / MAI-Transcribe ($0.18-$0.36/hr audio)
      → Transcribed text: "Photosynthesis kya hota hai?"
      → Normal Javaab pipeline (same as text input)

COST IMPACT:
  Average voice query: ~10 seconds of audio
  Cost per voice query: ~$0.001 (negligible)
  The real cost is still the LLM answering — same as text.

LANGUAGES: Hindi ✅ (excellent), Gujarati ✅ (good), English ✅

WHY NOT NOW:
  - Adds complexity to mobile app (recording, permissions, UI)
  - Need to handle noisy environments
  - Text + image covers 95%+ of use cases right now
  - Voice can be added as a feature update without architecture changes
```

---

## Part D — Execution

---

## 27. MVP Roadmap

| Week  | What                                                           | Deliverable           |
| ----- | -------------------------------------------------------------- | --------------------- |
| 1-2   | Knowledge base build (PDF extract, chunk, embed, index)        | Azure AI Search ready |
| 3-4   | Backend API (FastAPI, model router, RAG, cache, auth)          | Working /chat/ask     |
| 5-6   | Web app (Vite on app.tryjavaab.com, Swiggy-style design)       | Live web chat         |
| 7-8   | Mobile app (React Native), payment (Razorpay), referral system | Mobile beta           |
| 9-10  | Teacher portal, tickets, verified cache (5,000 answers)        | Admin ready           |
| 11-12 | Testing, beta (50 students), bug fixes, launch                 | **🚀 LAUNCH**         |

### One-Time Launch Costs

| Item                                  | Cost (₹)            |
| ------------------------------------- | ------------------- |
| PDF extraction (hybrid)               | ₹950                |
| Embedding generation                  | ₹86                 |
| Verified answer bank (AI generation)  | ₹2,350              |
| Verified answer bank (teacher review) | ₹15,000             |
| Google Play developer                 | ₹2,100              |
| Apple Developer (annual)              | ₹8,400              |
| Cursor Pro (3 months)                 | ₹5,040              |
| Replit (1 month Core)                 | ₹2,100              |
| Lovable Pro (1 month)                 | ₹2,100              |
| **Total**                             | **₹38,126 (~$454)** |

---

## 28. Student & Teacher Cheat Sheet

### 📚 Student Cheat Sheet — "Get Maximum Output, Spend Minimum Queries"

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 JAVAAB STUDENT CHEAT SHEET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE 1: ASK COMPLETE QUESTIONS
❌ Bad:  "Solve Q5"
✅ Good: "Solve Q5 from NCERT Class 10 Maths Chapter 4:
         Find the roots of 2x² - 5x + 3 = 0"
WHY: Complete questions = accurate answers in 1 query

RULE 2: MENTION YOUR BOARD + CLASS + SUBJECT
❌ Bad:  "What is photosynthesis?"
✅ Good: "Class 10 CBSE Science - Explain photosynthesis
         as per Chapter 6 Life Processes"
WHY: Javaab searches YOUR textbook specifically

RULE 3: ASK FOLLOW-UPS INSTEAD OF NEW QUESTIONS
❌ Wastes 2 queries:
   Query 1: "Explain Newton's second law"
   Query 2: "Give me the formula for Newton's second law"
✅ Saves 1 query:
   Query 1: "Explain Newton's second law with formula,
            derivation, and 2 numerical examples.
            CBSE Class 11 Physics Chapter 5."

RULE 4: USE IMAGE WISELY (Plus/Pro only)
✅ 1 clear photo of 1 question = 1 query, accurate answer
❌ Blurry photo = 1 wasted query + need to re-send
TIPS: Good lighting, crop to show ONLY the question,
      add text alongside: [photo] + "Solve — Class 10 Maths Ch.4"

RULE 5: KEEP PROFILE CONTEXT UPDATED (FREE — no query used)
  app.tryjavaab.com/settings
  Board, class, and language context help Javaab answer accurately.

RULE 6: RATE EVERY ANSWER (👍/👎) — does NOT cost a query
  Rating helps Javaab give YOU better answers over time.

RULE 7: REFER FRIENDS FOR BONUS QUERIES
  Share your code → Friend signs up → BOTH get 50 bonus queries!
  Your code: app.tryjavaab.com/refer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUERY BUDGET PLANNER (Free plan: 50 queries/month):
  22 school days × 4 queries/day = 88 queries
  + 12 weekend revision queries  = 12 queries
  ─────────────────────────────────────────────
  TOTAL: 50 queries ✅
  Allocation: 20 queries/subject/month = ~1/subject/school day
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 👨‍🏫 Teacher Cheat Sheet (Custom Plan)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 JAVAAB TEACHER CHEAT SHEET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUESTION PAPER GENERATOR
1. app.tryjavaab.com/admin/teacher → Question Papers (future Custom-plan module)
2. Select board, class, subject, chapters
3. Set difficulty mix: Easy/Medium/Hard
4. Set question types and marks
5. Click Generate → Download PDF with your institute logo!
TIP: Generate Sets A, B, C for the same exam to prevent cheating.

LESSON PLAN BUILDER
1. app.tryjavaab.com/admin/teacher → Lesson Plans (future Custom-plan module)
2. Select chapter + number of periods
3. AI creates period-wise plan
4. Edit and customize to your style → Export as PDF
TIP: Use "activity mode" for practical/lab chapters.

TEACHER TICKET ANSWERING
1. Check app.tryjavaab.com/admin/teacher/tickets daily
2. AI already attempted an answer — review it first
3. Your corrections make the system smarter
   (Every answer you provide helps ALL future students!)
4. Average time per ticket: 5-10 minutes
5. Use LaTeX for math: wrap formulas in \( ... \)

STUDENT MONITORING
1. app.tryjavaab.com/admin/teacher/analytics
2. See which topics students ask about most
3. Identify weak areas across your class
4. Focus teaching time on high-query topics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 29. V2 → V3 Changelog

### ✅ ADDED

| #   | Feature                                          | Reason                                                   |
| --- | ------------------------------------------------ | -------------------------------------------------------- |
| 1   | **Javaab API** (future B2B product)              | Revenue diversification; same infra powers both products |
| 2   | **Custom Plan** with formula-based pricing       | B2B coaching/schools = primary profit center             |
| 3   | **Question Paper Generator** (Custom)            | High-value feature teachers will pay for                 |
| 4   | **Lesson Plan Builder** (Custom)                 | High-value for coaching institutes                       |
| 5   | **Referral system**                              | CAC of ₹30 vs ₹200-500 for ads                           |
| 6   | **Razorpay integration** with GST breakdown      | Complete payment pipeline                                |
| 7   | **Query counting clarification** (message-based) | Critical for billing clarity                             |
| 8   | **GST (18%)** on all calculations                | Legal compliance for Indian SaaS                         |
| 9   | **Azure Key Vault**                              | Security best practice                                   |
| 10  | **Azure Container Registry**                     | Required for Container Apps deployments                  |
| 11  | **Azure Container Apps** (replaces App Service)  | True auto-scale to zero                                  |
| 12  | **Voice input** (future roadmap documented)      | Architecture readiness                                   |
| 13  | **Domain/URL architecture**                      | Cloudflare + subdomains                                  |
| 14  | **Break-even formulas**                          | Mathematical financial planning                          |
| 15  | **Student/Teacher cheat sheets**                 | Onboarding material                                      |
| 16  | **Pricing viability analysis** (honest)          | Transparent B2C loss-leader strategy                     |
| 17  | **Swiggy-style design direction**                | Modern Indian startup aesthetic                          |

### ❌ DROPPED

| #   | Feature                        | Reason                                                   |
| --- | ------------------------------ | -------------------------------------------------------- |
| 1   | **Azure Event Hub**            | Overkill for <1L users                                   |
| 2   | **Azure Service Bus / PubSub** | Synchronous API fine for current scale                   |
| 3   | **Kubernetes (AKS)**           | Container Apps gives same scaling without K8s complexity |
| 4   | **Azure SQL / PostgreSQL**     | Cosmos DB free tier covers all needs                     |
| 5   | **Azure App Service**          | Replaced by Container Apps (strictly better)             |
| 6   | **5 scale tiers**              | Simplified to 3 tiers                                    |

### 🔄 CHANGED

| #   | What             | V2                     | V3                                  |
| --- | ---------------- | ---------------------- | ----------------------------------- |
| 1   | Backend hosting  | App Service B1 ($13)   | Container Apps (auto-scale, ~$0-50) |
| 2   | Free plan        | 5 queries/day          | 50 queries/month                    |
| 3   | Plus plan        | ₹79/mo, 30 queries/day | ₹199/mo, 1,000 queries/month        |
| 4   | Pro plan         | ₹149/mo, unlimited     | ₹499/mo, unlimited                  |
| 5   | Scale tiers      | 5 tiers                | 3 tiers (1K, 10K, 1L)               |
| 6   | Pricing model    | Per-day limits         | Per-month limits (message-based)    |
| 7   | Revenue analysis | Optimistic             | Honest (B2C is loss-leader)         |

---

## 30. Vibe Coding Playbook — Zero to Launched App in 30 Days

### Tool Overview & Prompt Count

| Tool        | Prompts             | Purpose                                   | Days        |
| ----------- | ------------------- | ----------------------------------------- | ----------- |
| **Lovable** | 9 prompts (L1-L9)   | Web UI design                             | 1-3         |
| **Cursor**  | 23 prompts (C0-C22) | Backend, integration, deployment, testing | 4-27        |
| **Replit**  | 5 prompts (R1-R5)   | Mobile app                                | 15-22       |
| **Total**   | **37 prompts**      | **Zero to launched app**                  | **30 days** |

### Quick Reference: Which Tool, When

| Day   | Tool        | What You're Building                                                         |
| ----- | ----------- | ---------------------------------------------------------------------------- |
| 1-3   | **Lovable** | All web UI screens (L1-L9)                                                   |
| 4-5   | **Cursor**  | Project scaffolding + system prompt (C0-C2)                                  |
| 6-8   | **Cursor**  | Model router + RAG + cache + LLM services (C3-C7)                            |
| 9-12  | **Cursor**  | Chat endpoint + image + tickets (C8-C10)                                     |
| 13-17 | **Cursor**  | Connect frontend to backend (C11-C12)                                        |
| 15-22 | **Replit**  | React Native mobile app (R1-R5)                                              |
| 18-22 | **Cursor**  | Admin portal + teacher system (C13)                                          |
| 23-27 | **Cursor**  | Azure deployment + monitoring (C14-C15)                                      |
| 28-30 | **Cursor**  | Testing + seed data + launch (C16-C18) + Razorpay + Referral + QPG (C19-C22) |

---

### Setup Checklist (Before You Start)

```
□ Azure Account (azure.microsoft.com) — free $200 credit for 30 days
□ GitHub Account (github.com) — free
□ Cursor Account (cursor.com) — $20/mo Pro plan
□ Replit Account (replit.com) — free tier
□ Lovable Account (lovable.dev) — free tier (30 credits)
□ Google Play Developer ($25 one-time)
□ Apple Developer ($99/year) — can do later
```

---

### PROMPT C0: Create Project Rules File (`.cursorrules`)

```
Create a .cursorrules file in the project root with the following content:

# Javaab Project Rules

## Project Overview
Javaab (જવાબ / जवाब) is an AI-powered study assistant for Indian CBSE and
Gujarat Board (GSEB) students, Class 6-12. It supports English, Hindi, and
Gujarati in both native scripts and Roman transliteration.

## Tech Stack
- Backend: Python 3.12, FastAPI, uvicorn, async everywhere
- Web Frontend: Vite (React SPA), TypeScript, React, Tailwind CSS, framer-motion (for smooth micro-animations), lucide-react (for icons), shadcn/ui
- UI/UX Guidelines: Swiggy-inspired mobile-first design, clean aesthetics, visually premium with vibrant colors (Orange `#FC8019`, Green `#10B981`, Purple `#8B5CF6`)
- Mobile: React Native with Expo (managed workflow)
- Database: Azure Cosmos DB (free tier, serverless)
- Cache: Azure Redis Cache (C0 Basic)
- Search: Azure AI Search (Basic tier, hybrid vector + keyword)
- AI Models: Azure OpenAI (GPT-4.1, GPT-4.1-mini), Azure AI Foundry (Phi-4-mini)
- Embeddings: text-embedding-3-small via Azure OpenAI
- Storage: Azure Blob Storage
- Auth: current MVP uses local phone OTP mock + backend registration stub; production target is Azure AD B2C phone OTP
- Hosting: Azure Container Apps (backend), Azure Static Web Apps (frontend)

## Code Style Rules
- Python: Follow PEP 8, use type hints everywhere, async/await for all I/O
- TypeScript: Strict mode, no `any` types, use interfaces for objects
- React: Functional components only, hooks, no class components
- Naming: snake_case for Python, camelCase for TypeScript, PascalCase for components
- Current API responses are endpoint-specific JSON plus SSE for chat streaming; future public `/api/v1/*` endpoints should standardize on `{ success, data, error, metadata }`
- All environment variables: in .env files, never hardcoded
- Every function must have a docstring/JSDoc comment
- Error handling: Never silently catch errors, always log and return meaningful messages

## Architecture Rules
- Backend: routes → services → repositories (clean architecture)
- Frontend: Vite + React SPA, feature-based folders, React Router for navigation
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
```

---

### Phase 1: Lovable — Web UI Screens (Days 1-3)

> **Tool: Lovable (lovable.dev)** → Start new project → Use prompts L1-L9

#### PROMPT L1: Update Existing Website Pricing Page

```
Update the existing tryjavaab.com marketing website. This is a PURE marketing site —
no auth, no payments. Every CTA redirects to app.tryjavaab.com.

=== PRICING PAGE ===

Design: Swiggy-inspired. White bg (#FAFAFA), Cabinet Grotesk headings (font-black),
Outfit body, brand orange #FC8019 + near-black #1E1E1E, rounded-3xl cards,
generous whitespace. Mobile-first.

Annual/Monthly toggle at top. Default: Monthly. Annual shows "Save 20%" badge.

4 plan cards:

FREE — ₹0/month
  50 questions/month | Text only | All subjects & languages | 7-day history
  Button: "Start for Free" → app.tryjavaab.com (rounded-full, bg-[#1E1E1E])

PLUS — "For the Curious" — MOST POPULAR (elevated card, orange border)
  Monthly: ~~₹499~~ ₹199/mo | Annual: ~~₹5,988~~ ₹1,899/yr
  Show "60% OFF" orange badge
  1,000 questions/month | Text + Image | 90-day history
  Button: "Start Learning" → app.tryjavaab.com?plan=plus (rounded-full, bg-[#FC8019])

PRO — "For the Serious"
  Monthly: ~~₹999~~ ₹499/mo | Annual: ~~₹11,988~~ ₹4,791/yr
  Show "50% OFF" badge
  Unlimited questions | Priority AI | Teacher Tickets (3/month) | Unlimited history
  Button: "Go Pro" → app.tryjavaab.com?plan=pro (rounded-full, bg-[#1E1E1E])

CUSTOM — "For Schools & Coaching"
  Starting ₹3,869/month
  Question Paper Generator | Lesson Plans | Institute branding | Admin portal
  Button: "Contact Sales" → tryjavaab.com/contact (outline button)

Below cards:
- Feature comparison table (collapsible on mobile)
- "All prices include 18% GST" note in small text
- Referral callout strip: "📚 Refer a friend → both get 50 bonus questions free"

=== PRODUCTS PAGE ===

Two product cards in a bento grid:

JAVAAB AI — Available Now
  Chat-based AI tutor for Class 6–12, NCERT + GSEB
  Supports English, Hindi, Gujarati | Works on web + mobile
  CTA: "Try Javaab AI Free" → app.tryjavaab.com

JAVAAB API — Coming Soon (grayed/muted treatment, "Coming Soon" badge)
  Curriculum-aligned AI API for EdTech developers
  CTA: "Join Waitlist" → tryjavaab.com/contact

=== ALL CTAs ACROSS ENTIRE SITE ===

Every "Start Free", "Sign Up", "Get Started", "Try Now" → app.tryjavaab.com
Every plan-specific CTA → app.tryjavaab.com?plan=plus or ?plan=pro
No login/auth widget on tryjavaab.com at all.
```

#### PROMPT L2: Auth Screen

```
Build the authentication screen for app.tryjavaab.com.

BEHAVIOR:
- Any unauthenticated visit to app.tryjavaab.com (any route) → redirect to /login
- If URL had ?plan=plus or ?plan=pro, preserve it through auth → trigger upgrade
  flow automatically after login/onboarding

DESIGN:
Split layout on desktop (50/50). Single column on mobile. Swiggy-inspired. White bg (#FAFAFA), Cabinet Grotesk headings (font-black), Outfit body, brand orange #FC8019 + near-black #1E1E1E, rounded-3xl cards, generous whitespace. Mobile-first.

LEFT PANEL (branding):
  Large Cabinet Grotesk heading: "Sawaal kuch bhi ho."
  Sub: "Javaab turant milega."
  Small floating chips showing sample questions in EN/HI/GU:
    "What is photosynthesis?" | "ન્યૂટનના નિયમ સમજાવો" | "त्रिकोणमिति का सूत्र"
  Brand orange bg (#FC8019) with subtle pattern/texture, white text.

RIGHT PANEL (auth form):
  Javaab logo at top.

  STEP 1 — Phone Entry:
    Heading: "Enter your mobile number"
    Subtext: "We'll send you a 6-digit OTP. No password needed."
    Input: +91 prefix (non-editable) + 10-digit number field
    Large rounded-full CTA: "Send OTP"
    Below: "By continuing you agree to our Terms & Privacy Policy"

  STEP 2 — OTP Verification (replaces Step 1 in place, no page reload):
    Heading: "Enter the OTP"
    Subtext: "Sent to +91 XXXXXX1234" (masked)
    6-box OTP input (auto-advance focus, paste-friendly)
    Timer: "Resend OTP in 0:45" → becomes "Resend OTP" link after 0
    CTA: "Verify & Continue"
    Back link: "← Change number"

  New users (phone not in DB) → auto-redirect to onboarding after verify.
  Returning users → auto-redirect to /chat (or upgrade flow if ?plan param present).

No separate "Sign Up" vs "Login" distinction. Phone+OTP handles both.
```

#### PROMPT L3: Onboarding Flow (New Users Only)

```
Build a 4-step onboarding flow for first-time users at app.tryjavaab.com/onboarding.

Shown ONCE per user, immediately after first successful OTP verification.
Cannot be skipped. Can go back between steps.

Progress bar at top (fills orange as steps complete).

=== STEP 1 — Choose Your Board ===
Heading: "Which board do you study in?"
Two large tap-target cards (full width on mobile):
  CBSE (NCERT) — blue accent — "Class 6–12 | English + Hindi"
  Gujarat Board (GSEB) — orange accent — "Std 6–12 | Gujarati + English"
Auto-advance to Step 2 on selection.

=== STEP 2 — Select Your Class ===
Heading: "Which class are you in?"
Grid of chips: 6 | 7 | 8 | 9 | 10 | 11 | 12
Rounded-full chips, orange when selected.
"Next →" button becomes active on selection.

=== STEP 3 — Choose Your Language ===
Heading: "आप किस भाषा में पढ़ना चाहते हैं?"
(Translates to: "Which language do you want to study in?")
Three cards:
  English | हिन्दी | ગુજરાતી
Note below: "Don't worry — you can type in ANY language and Javaab will understand!"
Multi-select allowed. At least one required.

=== STEP 4 — You're All Set! ===
Large celebratory animation (confetti burst, not lottie dependency — CSS only).
"Welcome to Javaab! 🎉"
Show their profile summary: Board | Class | Language
Two CTAs:
  Primary: "Ask my first question →" → /chat
  Secondary: "Review my settings" → /settings

After onboarding completes:
  If URL had ?plan=plus or ?plan=pro → redirect to /subscribe?plan=plus/pro
  Else → redirect to /chat
```

#### PROMPT L4: Main Chat Interface

```
Build the main chat interface at app.tryjavaab.com/chat.

=== LAYOUT ===
Desktop: Fixed left sidebar (260px) + main chat area
Mobile: Bottom tab nav; sidebar as slide-in drawer

=== SIDEBAR ===
Top: Javaab logo + "New Chat" button (orange, rounded-full)
Middle: Conversation history list (date-grouped: Today, Yesterday, This Week)
  Each item: truncated question, subject chip, timestamp
  Active conversation: orange left border
Bottom:
  User avatar + name + tier badge (Free/Plus/Pro pill)
  Settings gear icon

=== HEADER (main area) ===
Left: Hamburger (mobile only)
Center: Current subject chip (e.g., "Class 10 · Science") — tappable to change
Right: Query counter ("47 left" for Free/Plus, "∞" for Pro) + avatar

=== CHAT AREA ===
Empty state (new chat):
  Center-aligned, large: "Sawaal kuch bhi ho. 📚"
  Quick-start chips (tappable, populate input):
    "Explain photosynthesis" | "Solve a quadratic" | "French Revolution causes"

Student messages: right-aligned, rounded-3xl, bg-[#FC8019]/10, orange text
AI messages: left-aligned, bg-white, shadow-sm, rounded-3xl
  Support: Markdown, LaTeX (\( x = \frac{-b}{2a} \)), numbered steps, tables
  Bottom of AI message:
    "📖 Source" collapsible (NCERT/GSEB book + chapter)
    Confidence badge: ✅ Verified | 🤔 AI Generated | ⚠️ Low Confidence
    Feedback: 👍 👎 (subtle, no query cost)

Typing indicator: 3 animated orange dots while AI is responding

=== INPUT AREA (fixed bottom) ===
Rounded-full pill container:
  📷 Camera icon (Plus/Pro) | 📎 Gallery icon (Plus/Pro)
  Text input: "पूछो कुछ भी... Ask anything..."
  Send button: orange circle with arrow
Image attached: thumbnail preview with ×remove inside the input pill

Free users: camera/gallery icons shown but tapping shows upgrade prompt modal.

=== RATE LIMIT HIT ===
When query limit reached, inline message in chat:
  "You've used all 50 free questions this month! 🚀
   Upgrade to Plus for 1,000 questions."
  Two buttons: "Upgrade to Plus ₹199/mo" | "Upgrade to Pro ₹499/mo"
  These open the subscription modal (built in L7).
```

#### PROMPT L5: Subject Browser (Future Backlog)

```
Build the subject browser only after the chat, tickets, subscription, settings,
and teacher portal flows are stable. The current web MVP does not register
`/subjects`; when this feature is added, register the route in `web/src/App.tsx`.

Target future route: app.tryjavaab.com/subjects.

=== TOP BAR ===
Board toggle: CBSE | GSEB (pill toggle, persists to user profile)
Class dropdown (6–12), defaults to user's class from onboarding

=== SUBJECT GRID ===
Bento-style asymmetric grid. Mix of wide and tall cards.
Subjects with icons + color accents:
  📐 Mathematics (blue) | 🔬 Science (green) | 🌍 Social Science (amber)
  📚 English (purple) | 📝 Hindi — CBSE / ✏️ Gujarati — GSEB only

Each card:
  Subject icon (large), subject name, "X chapters", "Y questions answered"
  Mini progress bar (% of chapters explored)
  Hover: slight lift + shadow

=== CHAPTER VIEW (click subject) ===
Breadcrumb: Subjects > Science
Chapter list (accordion):
  Ch.1 — Chemical Reactions | 3 questions answered | "Ask →" chip
  Ch.2 — Acids, Bases, Salts | ...
Clicking "Ask →" opens /chat with system context pre-set to that chapter

=== EMPTY STATE ===
If user hasn't asked anything yet: "Start asking questions to track your progress! 🎯"
```

#### PROMPT L6: Teacher Ticket Page (Pro Only)

```
Build Teacher Ticket page at app.tryjavaab.com/tickets.

=== ACCESS GATE ===
If user is Free or Plus → show locked state:
  Lock icon, "Teacher Tickets are a Pro feature"
  "Upgrade to Pro" CTA → opens subscription modal

=== HEADER (Pro users) ===
"🎓 Teacher Tickets"
Ticket usage: "2 of 3 used this month" (progress dots or mini bar)
"Raise New Ticket" button (disabled if 3/3 used, shows tooltip "Resets on [date]")

=== TICKET LIST ===
Card per ticket:
  Ticket ID (e.g., TKT-2604-001) | Question preview (2 lines) | Subject chip
  Status badge: ⏳ Open (amber) | 👀 With Teacher (blue) | ✅ Answered (green)
  Created: 2 days ago | Teacher: Mrs. Patel (when assigned)

=== TICKET DETAIL (/tickets/[id]) ===
Full question + image (if any)
"AI attempted but wasn't confident enough:" → gray box with AI's attempt
Teacher's answer: white card, full Markdown + LaTeX rendered
  "Answered by Mrs. Patel, Chemistry — 11 yrs exp" + timestamp
  👍 👎 feedback
"This answer has been saved to Javaab's knowledge base ✅" (if cache-added)
```

#### PROMPT L7: Subscription & Payment Flow (Inside app.tryjavaab.com)

```
Build the complete subscription flow entirely within app.tryjavaab.com.
NO redirect to tryjavaab.com. Payment happens inside the app.

=== ENTRY POINTS ===
1. User upgrades from /settings/subscription
2. User hits query limit in chat (inline prompt)
3. User arrives from tryjavaab.com with ?plan=plus or ?plan=pro in URL
4. User taps a locked feature (image upload, teacher tickets)

=== SUBSCRIBE PAGE (/subscribe) ===
Sticky header: "Choose your plan"
Toggle: Monthly | Annual (save 20%)

Two cards (Plus and Pro — Free is already active):

PLUS — ₹199/mo
  List: ✓ 1,000 questions/month ✓ Image input ✓ 90-day history
  CTA: "Upgrade to Plus" → triggers Razorpay

PRO — ₹499/mo (recommended badge)
  List: ✓ Everything in Plus ✓ Unlimited questions ✓ Teacher Tickets ✓ Priority AI
  CTA: "Upgrade to Pro" → triggers Razorpay

Below: "All plans include 18% GST • Cancel anytime • Secure payment via Razorpay"
UPI / Visa / Mastercard / RuPay trust logos

=== RAZORPAY CHECKOUT ===
Opens Razorpay's hosted checkout (or their embedded widget).
DO NOT build a custom card form — use Razorpay SDK.
Pass: amount, plan name, user's phone (pre-filled), user's name.

=== SUCCESS STATE ===
Full-screen success screen (not a modal):
  Confetti animation (CSS)
  "You're now a Javaab [Plus/Pro] member! 🎉"
  Show new benefit unlocked (e.g., "You now have 1,000 questions this month")
  "Start asking →" button → /chat
  Small text: "Download invoice" link

=== SETTINGS > SUBSCRIPTION (/settings/subscription) ===
Current plan display: tier badge, billing date, queries used this month
Upgrade button (if not Pro) → /subscribe
Cancel subscription: subtle link, confirmation modal before cancellation
  On cancel: "Active until [end of billing period]"
Invoice history: date, amount, download PDF link
```

#### PROMPT L8: Referral Dashboard

```
Build the referral page at app.tryjavaab.com/refer.

=== HEADER ===
"Refer friends, earn free questions 🎁"
Subtext: "You both get 50 bonus questions when they join."

=== REFERRAL CODE BLOCK ===
Large display: JAVAAB-[USERNAME]-[4-DIGIT]
"Copy Code" button (copies to clipboard, shows ✓ Copied feedback)
WhatsApp share button (deep link: wa.me/?text=...) — primary CTA, green
"Share Link" button (copies full URL)
QR code (generated, downloadable)

=== HOW IT WORKS ===
3-step horizontal strip:
  1. Share your code → 2. Friend signs up → 3. Both get 50 bonus questions

=== YOUR STATS ===
Cards: Referred | Joined | Bonus Questions Earned | Next milestone
"Refer 5 this month → get 1 month Plus FREE"
"Refer 10 this month → get 1 month Pro FREE"
Progress bar toward current milestone

=== REFERRAL HISTORY TABLE ===
Name (masked — "R***h"), Date joined, Status (Signed up / Completed 5 queries / Reward granted)

=== LEADERBOARD (optional, collapsible) ===
Top referrers this month. Gamification. Anonymized names.
```

#### PROMPT L9: Push to GitHub

```
Connect this Lovable project to GitHub.

Repository: [your-github-username]/javaab-web
Branch: main
Include all screens built in L1-L8.

Folder structure within the export:
  /app/(auth)/login         → L2 auth screens
  /app/(auth)/onboarding    → L3 onboarding
  /app/(main)/chat          → L4 chat interface
  /app/(main)/subjects      → L5 subject browser (future/backlog)
  /app/(main)/tickets       → L6 teacher tickets
  /app/(main)/subscribe     → L7 subscription + payment
  /app/(main)/refer         → L8 referral
  /app/(main)/settings      → settings shell
  /app/(main)/settings/subscription → subscription settings
  /app/(admin)/teacher/*    → teacher portal routes

Ensure all internal links use React Router <Link> components.
All ?plan= query params are read and stored in sessionStorage
during auth so they survive the OTP verification redirect.

I'll continue development in Cursor.
```

---

### Phase 2: Cursor — Build the Backend (Days 4-12)

> **Tool: Cursor (cursor.com)** → Agent Mode (Cmd+I or Ctrl+I)

#### PROMPT C1: Project Scaffolding

```
@agent Set up the complete Javaab monorepo project structure.

javaab/
├── .cursorrules
├── .github/workflows/
│   ├── backend-ci.yml
│   ├── web-deploy.yml
│   └── mobile-build.yml
├── backend/
│   ├── app/
│   │   ├── main.py               (FastAPI app entry point)
│   │   ├── config.py             (pydantic-settings environment config)
│   │   ├── routes/
│   │   │   ├── chat.py           (POST /chat/ask, /chat/feedback)
│   │   │   ├── auth.py           (login, register, profile)
│   │   │   ├── subjects.py       (browse subjects/chapters)
│   │   │   ├── tickets.py        (teacher ticket CRUD — Pro only)
│   │   │   └── admin.py          (teacher portal endpoints)
│   │   ├── services/
│   │   │   ├── model_router.py   (4-tier model routing)
│   │   │   ├── rag_service.py    (RAG pipeline — search + context building)
│   │   │   ├── cache_service.py  (verified answer cache)
│   │   │   ├── llm_service.py    (Azure OpenAI + AI Foundry API calls)
│   │   │   ├── image_service.py  (image processing + OCR)
│   │   │   ├── language_service.py  (language/script detection)
│   │   │   ├── ticket_service.py (teacher ticket business logic)
│   │   │   ├── payment_service.py (Razorpay)
│   │   │   ├── referral_service.py (referral system)
│   │   │   └── math_validator.py (SymPy-based math validation)
│   │   ├── repositories/
│   │   │   ├── cosmos_repo.py    (Azure Cosmos DB)
│   │   │   ├── redis_repo.py     (Redis cache)
│   │   │   └── search_repo.py    (Azure AI Search)
│   │   ├── models/
│   │   │   ├── schemas.py        (Pydantic request/response schemas)
│   │   │   ├── student.py
│   │   │   ├── conversation.py
│   │   │   └── ticket.py
│   │   ├── middleware/
│   │   │   ├── rate_limiter.py   (tier-based rate limiting)
│   │   │   └── auth_middleware.py
│   │   └── prompts/
│   │       └── system_prompt.py  (Master system prompt)
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── web/                          (populated from Lovable export)
├── mobile/                       (built in Replit)
├── scripts/
│   ├── ingest_ncert.py
│   ├── ingest_gseb.py
│   ├── build_verified_cache.py
│   └── seed_test_data.py
├── docker-compose.yml
└── README.md

For each Python file: proper imports, class/function stubs with docstrings,
type hints, TODO comments.

Config (pydantic-settings):
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY
  AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_KEY
  AZURE_REDIS_HOST, AZURE_REDIS_KEY
  AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY
  AZURE_BLOB_CONNECTION_STRING, PHI4_MINI_ENDPOINT, PHI4_MINI_KEY

FastAPI: CORS for localhost:3000, /health endpoint, error handling middleware.
```

#### PROMPT C2: Master System Prompt

```
@agent Create backend/app/prompts/system_prompt.py

Store the complete Javaab master system prompt (from Section 21 of this document)
as a Python constant BASE_SYSTEM_PROMPT.

Also create:
def build_system_message(class_level: int, board: str, subject: str, tier: str) -> str:
    return f"""
{BASE_SYSTEM_PROMPT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STUDENT CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Class: {class_level}
- Board: {board}
- Subject: {subject}
- Subscription Tier: {tier}
"""
```

#### PROMPT C3: 4-Tier Model Router (The Brain)

```
@agent Implement model_router.py — the MOST CRITICAL service in Javaab.
It decides which AI model handles each query.

TIER 0 — VERIFIED CACHE:
- Query Azure AI Search "verified_answers" index (HNSW, with metadata filters)
- If similarity >= 0.93 → cache HIT → retrieve from Redis → return immediately
- Log: cache_hit=True

TIER 1 — PHI-4-MINI (simple queries):
- Classify complexity using Phi-4-mini (~100 tokens)
- SIMPLE = definitions, factual recall, "what is", direct answers
- COMPLEX = calculations, multi-step, proofs, analysis, comparisons
- If SIMPLE → route to Phi-4-mini (Azure AI Foundry endpoint)

TIER 2 — GPT-4.1-mini (medium + image):
- MEDIUM complexity → GPT-4.1-mini
- If image query → ALWAYS GPT-4.1-mini for OCR first, then reclassify

TIER 3 — GPT-4.1 (complex):
- COMPLEX → GPT-4.1
- Multi-step math, physics numericals, proofs, detailed reasoning

Implementation requirements:
- Async throughout (httpx for API calls)
- Track token usage and cost per query (log to Cosmos DB)
- Retry with exponential backoff (3 retries)
- Fallback: if Phi-4-mini fails → GPT-4.1-mini
- Streaming responses (SSE) for all tiers
- Circuit breaker: if model fails 5x in 1 minute, skip it
- Return ModelRouterResponse: answer, model_used, tokens_in, tokens_out,
  cost, confidence, from_cache, sources[]
```

#### PROMPT C4: RAG Pipeline

```
@agent Implement rag_service.py.

HYBRID SEARCH:
1. Apply metadata filters FIRST (board, class_level, subject)
2. Run HYBRID search simultaneously:
   - Vector: embed query via text-embedding-3-small, cosine similarity
   - Keyword: BM25 full-text search for exact term matches
   - Merge results using Reciprocal Rank Fusion (RRF)
3. Return top 5 chunks

CROSS-LINGUAL SEARCH (for non-English queries):
1. Search directly with original query (finds vernacular chunks)
2. Translate query to English via Phi-4-mini (~50 tokens, ~$0.00002)
3. Search again with English translation (finds NCERT English chunks)
4. Merge both sets, deduplicate, return top 5

CONTEXT BUILDER:
- Format top 5 chunks: "--- Source 1: NCERT Class 10 Science, Ch.6, Page 95 ---\n[content]..."
- Ensure under 2,500 tokens (truncate if needed)

CONFIDENCE SCORING:
- Avg similarity > 0.80 → HIGH | 0.60-0.80 → MEDIUM | < 0.60 → LOW | < 0.40 → NONE

Use Azure AI Search Python SDK (azure-search-documents). All operations async.
On search failure: return empty context (don't crash — let LLM try its best).
```

#### PROMPT C5: Verified Answer Cache Service

```
@agent Implement cache_service.py.

ARCHITECTURE:
- MATCHING: Azure AI Search "verified_answers" index (HNSW) — O(log n)
- STORAGE: Redis (key-value by cache_id) — O(1), ~0.1ms

METHODS:

1. async check_cache(query, board, class_level, subject) → Optional[CachedAnswer]:
   - Embed query with text-embedding-3-small
   - HNSW search in "verified_answers" with metadata filters, top_k=1
   - If similarity >= 0.93: GET from Redis by cache_id → return CachedAnswer
   - Else: return None

2. async store_verified_answer(answer: VerifiedAnswer):
   - Generate embedding for question
   - Upsert into AI Search "verified_answers"
   - SET in Redis: key=cache_id, value=JSON, TTL=None

3. async get_cache_stats() → CacheStats:
   - Total count, hit rate, top uncached questions

VerifiedAnswer data model:
{ cache_id, question, question_embedding, answers: {en, hi, gu},
  board, class_level, subject, chapter, verified_by, verified_at, source_citation }
```

#### PROMPT C6: LLM Service

```
@agent Implement llm_service.py.

THREE MODEL CLIENTS:
1. Phi-4-mini (Azure AI Foundry): httpx, streaming, text classification
2. GPT-4.1-mini (Azure OpenAI): openai SDK, streaming, vision support for OCR
3. GPT-4.1 (Azure OpenAI): openai SDK, streaming, complex reasoning

METHODS:
- async generate_response(model, system_prompt, user_message, context,
    image_base64=None, temperature=0.15, max_tokens=1500, stream=True)
    → AsyncGenerator[str, None]  # yields SSE chunks

- async classify_query(query: str) → QueryComplexity  # SIMPLE/MEDIUM/COMPLEX
- async extract_text_from_image(image_base64: str) → str  # GPT-4.1-mini Vision
- async translate_to_english(text: str) → str  # Phi-4-mini, ~50 tokens

IMPORTANT:
- Track input_tokens, output_tokens, model_name per call
- Retry with exponential backoff (3 retries on 429)
- Temperature = 0.15 for factual accuracy
- All methods async; for streaming: yield each chunk as it arrives
```

#### PROMPT C7: Image Processing Service

```
@agent Implement image_service.py using Pillow (PIL).

PIPELINE:
1. validate_image(image_bytes) → bool
   - Max 5MB raw, JPEG/PNG/WEBP only, not corrupted

2. optimize_image(image_bytes) → bytes
   - Resize to max 1024px on longest side
   - Convert to JPEG, compress to under 1MB
   - Auto-rotate from EXIF, strip EXIF metadata (privacy)

3. extract_question(image_base64: str) → ImageExtractionResult
   - GPT-4.1-mini Vision with prompt:
     "You are an OCR assistant for Indian CBSE/GSEB students.
      Extract the exact question from this image.
      If math, convert to LaTeX. If diagram, describe and label all parts.
      If Hindi (Devanagari) or Gujarati script, preserve accurately.
      If image is unclear, say so specifically."
   - Return: extracted_text, detected_language, detected_subject, is_clear

All I/O async.
```

#### PROMPT C8: Chat Endpoint (Full Pipeline)

```
@agent Implement routes/chat.py — the MAIN endpoint students hit.

POST /chat/ask pipeline:
1. Validate input + check rate limits (Free: 50/mo, Plus: 1000/mo, Pro: unlimited)
2. If image → optimize → extract_question via image_service
3. Detect language/script
4. Check verified cache (cache_service.check_cache)
   → Cache HIT: return immediately with from_cache=True
5. Cache MISS → RAG retrieval (rag_service.retrieve_context)
6. Build system prompt with student context
7. Route to appropriate model (model_router)
8. Stream response via SSE

STREAMING SSE FORMAT:
data: {"type": "chunk",    "content": "..."}
data: {"type": "metadata", "model": "phi-4-mini", "confidence": "high"}
data: {"type": "sources",  "sources": [...]}
data: {"type": "done"}

AFTER RESPONSE (async, non-blocking):
- Save conversation to Cosmos DB
- Log usage metrics (model, tokens, cost, confidence)
- If confidence LOW → flag for potential cache addition

RATE LIMIT (429) message:
"You've used all your free questions this month! 📚
 Upgrade to Javaab Plus for 1,000 questions/month."

Also implement POST /chat/feedback:
- Save thumbs up/down with message_id to Cosmos DB
- Flag answers with >20% thumbs down for review
```

#### PROMPT C9: Teacher Ticket System

```
@agent Implement the complete Teacher Ticket system.

1. routes/tickets.py:
   POST /tickets/create (Pro only):
   - Verify Pro tier + tickets_used_this_month < 3
   - Create ticket in Cosmos DB:
     ticket_id (TKT-{date}-{sequence}), student question, image (if any),
     ai_attempts (Layer 3 and 4 answers), status: "OPEN"

   GET /tickets — list all tickets for current student
   GET /tickets/{ticket_id} — full detail with teacher answer if resolved

2. routes/admin.py (Teacher Portal):
   GET /admin/tickets?status=OPEN — sorted by oldest first
   POST /admin/tickets/{id}/assign — assign to teacher
   POST /admin/tickets/{id}/respond:
   - Teacher submits answer
   - Update status to "RESOLVED"
   - AUTOMATICALLY add Q&A to verified answer cache
   - Send push notification to student

3. ticket_service.py:
   - Monthly ticket count check
   - Round-robin auto-assign by subject
   - Escalation: if open > 48hrs → alert admin

CRITICAL: Every resolved ticket AUTOMATICALLY becomes a verified cached answer.
This means every ticket makes the system smarter.
```

#### PROMPT C10: PDF Ingestion Pipeline

```
@agent Implement scripts/ingest_ncert.py and scripts/ingest_gseb.py.

HYBRID EXTRACTION STRATEGY:
For each PDF page:
1. TRY PyMuPDF first (FREE):
   Quality check: len(text) > 50 chars? Valid Unicode? Garbage ratio < 5%?
   ALL YES → use PyMuPDF (FREE) ✅
   ANY NO  → Azure Document Intelligence "Read" model ($1.50/1000 pages)

CHUNKING:
- Chunk size: 500-800 tokens, overlap: 100 tokens
- Split on: paragraph → sentence → word boundaries
- Metadata per chunk: board, class, subject, chapter_number, chapter_name,
  topic, language, source_type, page_number

EMBEDDING + INDEXING:
- text-embedding-3-small (batch 100 chunks at a time)
- Upload to Azure AI Search "textbook_chunks" index:
  chunk_id (key), content, content_vector (1536 dims), all metadata fields

Add: progress bar (tqdm), error handling for corrupt PDFs,
resume capability (JSON manifest of processed files).

Usage:
  python scripts/ingest_ncert.py --pdf-dir ./data/ncert/ --board CBSE
  python scripts/ingest_gseb.py --pdf-dir ./data/gseb/ --board GSEB
```

---

### Phase 3: Cursor — Connect Frontend to Backend (Days 13-17)

#### PROMPT C11: Import Lovable UI + Connect APIs

```
@agent Connect the Lovable Vite frontend (/web) to the FastAPI backend.

1. API client service (web/src/services/api.ts):
   - Base URL from environment variable
   - Current MVP: localStorage-backed auth state plus backend registration/profile calls
   - Production target: JWT/session auth in httpOnly cookie
   - SSE streaming support for chat
   - Image compression client-side and base64 payloads for chat/ticket APIs
   - Error handling with user-friendly messages

2. Connect Chat Interface to POST /chat/ask:
   - SSE streaming: display chunks as they arrive (typewriter effect)
   - Show "Thinking..." indicator while waiting for first chunk
   - On "metadata" event → show model and confidence badge
   - On "sources" event → show collapsible citations
   - Handle image: compress client-side → send as base64
   - Handle 429: show upgrade prompt

3. Connect feedback buttons (👍/👎) to POST /chat/feedback
4. Connect onboarding to POST /auth/register and POST /student/profile
5. Keep GET /subjects/{board}/{class_level} available for the future subject browser

6. Add LaTeX rendering:
   - Install KaTeX
   - Create MarkdownWithMath component
   - Test: \( x = \frac{-b \pm \sqrt{b^2-4ac}}{2a} \)

7. Add i18n (react-i18next): locale files en.json, hi.json, gu.json

8. Font setup: Noto Sans + Noto Sans Devanagari + Noto Sans Gujarati
```

#### PROMPT C12: Real-time Streaming Chat Component

```
@agent Build web/src/components/chat/ChatStream.tsx.

- EventSource (SSE) connection to /chat/ask
- Parse chunks, append to message in real-time
- Markdown rendering (react-markdown) + LaTeX (KaTeX)
- Auto-scroll to bottom as content arrives
- "Javaab is thinking..." typing indicator
- Error handling: retry button on network failure, "Rate limit reached" on 429
- On stream complete:
  - Source citations in collapsible section
  - Confidence badge (✅ Verified / 🤔 AI Generated)
  - Feedback buttons (👍 👎)
  - Re-enable input
- Dark mode (Tailwind dark: classes)
- Accessibility: ARIA labels, keyboard navigation
```

---

### Phase 4: Replit — React Native Mobile App (Days 15-22)

> **Tool: Replit** → React Native (Expo) template

#### PROMPT R1: Mobile App Setup

```
Create React Native app using Expo (TypeScript, managed workflow) for "Javaab".

SETUP:
- Expo Router (file-based routing)
- NativeWind (Tailwind CSS for React Native)
- React Native Async Storage, Expo Camera, Expo Image Picker

SCREENS:
1. (auth)/login — Phone number OTP login
2. (auth)/onboarding — Board → Class → Language (4 steps)
3. (tabs)/chat — Main chat interface (TAB 1)
4. (tabs)/subjects — Subject browser (TAB 2)
5. (tabs)/profile — Settings and subscription (TAB 3)
6. tickets — Teacher ticket list (Pro only)
7. ticket/[id] — Ticket detail

NAVIGATION: Bottom tab bar (Chat, Subjects, Profile)
THEME: Blue #2563EB, Orange #F97316, dark mode support
FONTS: Noto Sans (EN), Noto Sans Devanagari (HI), Noto Sans Gujarati (GU)
```

#### PROMPT R2: Mobile Chat Interface

```
Build the main Chat screen:

LAYOUT:
- Header: "Javaab 📚" + subject selector + settings icon
- Chat: FlatList, auto-scroll to bottom
- Fixed bottom input: TextInput + camera button + gallery button + send button
- Image preview thumbnail with X when attached

MESSAGE BUBBLES:
- Student: right-aligned, blue, white text
- AI: left-aligned, white/light gray, renders Markdown + LaTeX + emojis
  + collapsible "📖 Source" section
  + confidence badge + feedback buttons (👍 👎)

STREAMING: typing indicator (three animated dots), append chunks via SSE

IMAGE CAPTURE FLOW:
1. Camera tap → Expo Camera full screen → preview → "Retake" or "Use Photo"
2. On "Use Photo" → compress to <1MB JPEG → attach to message
3. Gallery: same flow via Image Picker

OFFLINE: Cache last 20 conversations in AsyncStorage,
         show "You're offline" banner, queue messages
```

#### PROMPT R3: Camera & Image Processing

```
Implement camera and image processing for Javaab mobile.

CameraCapture.tsx (expo-camera):
- Viewfinder with guidelines ("Align question within frame")
- Flash toggle, capture button, after capture: "Retake" and "Use Photo"
- Permission handling with friendly message if denied

imageProcessor.ts (expo-image-manipulator):
1. Resize to max 1024px on longest side
2. Compress JPEG quality 0.7
3. If still > 1MB → quality 0.5 → resize 768px
4. Convert to base64
5. Return: { base64, width, height, sizeKB }

GalleryPicker.tsx (expo-image-picker):
- Single image selection, same optimization pipeline, loading indicator
```

#### PROMPT R4: Mobile API Client & Auth

```
Build API client and authentication service.

src/services/api.ts:
- Axios-based, base URL from env config
- Auth token in expo-secure-store, auto-attached to all requests
- SSE via EventSource polyfill (react-native-sse)
- Request interceptor: auth token
- Response interceptor: 401 → login, 429 → upgrade prompt
- Timeout: 30s for chat, 10s for others
- Retry: 3 attempts with backoff for 5xx

src/services/auth.ts: sendOTP, verifyOTP (store JWT), logout, getProfile
src/services/chat.ts: sendMessage (SSE), sendFeedback, getConversations
src/services/tickets.ts (Pro): createTicket, getTickets, getTicket
```

#### PROMPT R5: Export Mobile App to GitHub

```
Export this project to GitHub:
Repository: [your-github-username]/javaab-mobile
Branch: main

Then clone into the /mobile directory of the main Javaab monorepo in Cursor.
```

---

### Phase 5: Cursor — Admin Portal & Teacher Tickets (Days 18-22)

#### PROMPT C13: Teacher Admin Portal

```
@agent Build the Teacher Admin Portal in Vite.

Route: /admin/teacher (protected — role="teacher" only)

PAGES:
1. /admin/teacher/dashboard:
   Stats: Open Tickets | In Progress | Resolved Today | Avg Response Time
   Quick filters: by subject, class, urgency

2. /admin/teacher/tickets:
   Table: Ticket ID, Student Class, Subject, Question Preview, Status, Date, Action
   Filters: Open / In Progress / Resolved | Sort: Oldest first (default)

3. /admin/teacher/tickets/[id]:
   - Student's original question + image
   - AI's attempted answers (Layer 3 and Layer 4) in gray boxes
   - ANSWER INPUT: rich text + Markdown + LaTeX preview + image upload
   - On submit: POST /admin/tickets/{id}/respond
   - Success message: "Answer sent! Also cached so future students
     get instant answers for this question."

4. /admin/teacher/analytics:
   Tickets answered this month, avg student rating, common topics,
   resolution time trends

Keep UI clean and efficient (shadcn/ui). Mobile-responsive (teachers use phones).
```

---

### Phase 6: Cursor — Deploy to Azure (Days 23-27)

#### PROMPT C14: Docker & Azure Deployment

```
@agent Set up the complete deployment pipeline for Javaab on Azure.

1. BACKEND DEPLOYMENT (Azure Container Apps):

   Dockerfile:
   - Python 3.12 slim base
   - Install requirements.txt
   - Run with uvicorn, 4 workers
   - Health check on /health, expose port 8000

   docker-compose.yml (local dev):
   - Backend service (FastAPI), Redis service, .env variables

2. WEB DEPLOYMENT (Azure Static Web Apps):

   .github/workflows/web-deploy.yml:
   - Trigger: push to main, changes in /web/**
   - Build Vite (React SPA), deploy to Azure Static Web Apps

3. AZURE INFRASTRUCTURE SCRIPT (scripts/setup_azure.sh):

   az group create --name javaab-rg --location centralindia
   az containerapp env create --name javaab-env --resource-group javaab-rg
   az containerapp create --name javaab-api ... (Container Apps, not App Service)
   az cognitiveservices account create --name javaab-openai ... --location eastus
   az search service create --name javaab-search ... --sku basic
   az redis create --name javaab-cache ... --sku Basic --vm-size C0
   az cosmosdb create --name javaab-db ... --enable-free-tier true
   az storage account create --name javaabstorage ...
   az staticwebapp create --name javaab-web ...
   az keyvault create --name javaab-vault ...
   az acr create --name javaabregistry --sku Basic

   Print all connection strings. Save to .env.production.

4. CI/CD (.github/workflows/backend-ci.yml):
   On push to main (backend/** changes):
   Run pytest → Build Docker → Push to ACR → Deploy to Container Apps → Health check

5. Create .env.example with ALL required variables documented.
```

#### PROMPT C15: Monitoring & Alerts

```
@agent Set up Azure Application Insights monitoring.

1. Backend instrumentation (opencensus-ext-azure):
   Track every /chat/ask:
   - Response time, model used, tokens consumed
   - Cache hit/miss, confidence, student tier, board, class, subject, language
   Custom metrics:
   - "javaab.query.cost", "javaab.cache.hit_rate", "javaab.model.usage"
   - "javaab.ticket.created", "javaab.feedback.positive_rate"

2. Alert rules:
   - Error rate > 5% in 5 minutes → email
   - Avg response > 10 seconds → email
   - Cache hit rate < 15% → email
   - Any model returning 429 → email
   - Teacher ticket open > 48 hours → email

3. Dashboard:
   Real-time: Active users, queries/min, avg response time
   Daily: Total queries, cost by model, cache hit rate
   Weekly: Student growth, popular subjects, feedback trends
```

---

### Phase 7: Testing & Launch (Days 28-30)

#### PROMPT C16: Test Suite

```
@agent Create backend/tests/ comprehensive test suite.

1. test_model_router.py:
   - Cache hit returns verified answer instantly
   - Simple query routes to Phi-4-mini
   - Medium query routes to GPT-4.1-mini
   - Complex math routes to GPT-4.1
   - Image query routes to GPT-4.1-mini for OCR
   - Fallback: Phi-4-mini fails → GPT-4.1-mini
   - Rate limiting: Free user blocked after 50 queries

2. test_rag_service.py:
   - Hybrid search returns relevant chunks
   - Metadata filtering (board, class, subject)
   - Cross-lingual search (Hindi query finds English chunks)
   - Confidence scoring thresholds, empty results handling

3. test_cache_service.py:
   - Cache hit with similarity > 0.93 returns answer
   - Cache miss with low similarity returns None
   - Store and retrieve verified answer
   - Metadata filtering in cache search

4. test_tickets.py:
   - Pro user can create ticket
   - Free user cannot create ticket (403)
   - Max 3 tickets/month enforcement
   - Teacher can respond to ticket
   - Resolved ticket auto-adds to verified cache

5. test_chat_endpoint.py (integration):
   - Full pipeline: text query → RAG → model → streamed response
   - Image query pipeline
   - Hindi query → cross-lingual search → Hindi response
   - Gujarati Roman script detection
   - Feedback endpoint

6. test_language_detection.py:
   - English, Hindi Devanagari, Gujarati script detection
   - Roman Hindi (Hinglish) and Roman Gujarati detection
   - Mixed language detection

Use pytest, pytest-asyncio, unittest.mock for Azure services.
Makefile: make test, make test-fast, make lint, make format
```

#### PROMPT C17: Seed Data & Knowledge Base Build

```
@agent Create scripts/seed_test_data.py.

1. 5 test student accounts:
   1 Free, 1 Plus, 1 Pro, 2 Free — mix of CBSE/GSEB, different classes

2. 50 sample verified answers:
   10 Math (classes 8-12) + 10 Science + 10 Social Science
   + 10 English + 5 Hindi + 5 Gujarati
   Each with answers in EN, HI, GU | realistic citations | LaTeX math in math answers

3. 5 sample teacher accounts (each assigned 1-2 subjects)

4. 3 sample teacher tickets (1 Open, 1 In Progress, 1 Resolved)

5. 10 sample conversation histories (mix of subjects/languages/complexity)

Print summary: "✅ Seeded: 5 students, 50 verified answers, 5 teachers,
 3 tickets, 10 conversations"
```

#### PROMPT C18: Final Pre-Launch Checklist

```
@agent Create LAUNCH_CHECKLIST.md in the project root.

## Infrastructure ✅
- [ ] Azure Container Apps running and healthy (/health → 200)
- [ ] Azure Static Web Apps deployed (web accessible)
- [ ] Azure AI Search indexes created (textbook_chunks + verified_answers)
- [ ] Azure Redis Cache connected
- [ ] Azure Cosmos DB collections created
- [ ] Azure Blob Storage containers created
- [ ] Azure OpenAI models deployed (GPT-4.1, GPT-4.1-mini)
- [ ] Azure AI Foundry Phi-4-mini endpoint active
- [ ] Azure Key Vault configured with all secrets
- [ ] SSL certificates valid for all endpoints
- [ ] Custom domain configured (app.tryjavaab.com)

## Knowledge Base ✅
- [ ] All NCERT PDFs (Class 6-12, EN+HI) ingested and indexed
- [ ] All GSEB PDFs (Std 6-12, GU+EN) ingested and indexed
- [ ] NCERT Exemplar + Previous year papers indexed
- [ ] Total chunks in index: ~102,000 (verify count)
- [ ] Verified Answer Bank: 5,000+ answers loaded
- [ ] Cross-lingual search tested for all 3 languages

## App Features ✅
- [ ] Web chat working with streaming
- [ ] Mobile chat working with streaming
- [ ] Image upload and OCR working
- [ ] LaTeX rendering working on web and mobile
- [ ] Hindi Devanagari input/output working
- [ ] Gujarati script input/output working
- [ ] Roman Hindi (Hinglish) and Roman Gujarati working
- [ ] Onboarding flow complete
- [ ] Teacher ticket creation working (Pro only)
- [ ] Teacher admin portal working
- [ ] Rate limiting working per tier
- [ ] Dark mode working

## Security ✅
- [ ] All API keys in Azure Key Vault (not in code)
- [ ] Authentication working (phone OTP)
- [ ] Input validation on all endpoints
- [ ] CORS configured correctly
- [ ] No sensitive data in logs

## Monitoring ✅
- [ ] Application Insights connected with custom metrics
- [ ] Alert rules configured (error rate, response time, cache hit rate)

## Testing ✅
- [ ] All unit tests passing
- [ ] 100 sample queries tested across all subjects/languages/boards
- [ ] Cache hit rate > 20% on sample queries
- [ ] Average response time < 5 seconds
- [ ] Load test: 50 concurrent users handled

## Payments ✅
- [ ] Razorpay integration working (Plus + Pro subscriptions)
- [ ] GST-compliant invoices generating
- [ ] Webhook handling tested (subscription.activated, payment.failed)

## Store Submission ✅
- [ ] Google Play Store listing prepared
- [ ] App icons and screenshots ready (all 3 languages)
- [ ] Privacy policy + Terms of service pages created

## 🚀 LAUNCH
- [ ] Beta group of 50 students tested for 3 days
- [ ] Critical bugs from beta fixed
- [ ] GO LIVE!
```

#### PROMPT C19: Razorpay Payment Integration

```
@agent Integrate Razorpay payment gateway.

1. Install razorpay Python SDK

2. backend/app/services/payment_service.py:
   - create_subscription(user_id, plan: "plus"|"pro"):
     → Razorpay Subscriptions API, return subscription_id + payment_link

   - handle_webhook(payload, signature):
     → Verify Razorpay webhook signature
     → Handle: "subscription.activated" → upgrade tier
                "subscription.charged" → log payment
                "subscription.cancelled" → downgrade to Free
                "payment.failed" → mark payment_due, send reminder

   - cancel_subscription(user_id) → downgrade at end of billing period
   - get_billing_history(user_id) → payment history from Cosmos DB

3. Routes:
   POST /payments/subscribe, POST /payments/webhook (signature verify)
   POST /payments/cancel, GET /payments/history
   GET /payments/invoice/{id} — PDF invoice with GST

4. Pre-create Razorpay plans:
   javaab_plus_monthly: ₹199.00/mo | javaab_pro_monthly: ₹499.00/mo
   javaab_plus_annual: ₹1,899.00/yr | javaab_pro_annual: ₹2,869.00/yr

Store Razorpay API keys in Azure Key Vault, NOT in .env files.
```

#### PROMPT C20: Referral System

```
@agent Build the complete referral system.

1. backend/app/services/referral_service.py:
   - generate_referral_code(user_id) → "JAVAAB-{USERNAME}-{4-DIGIT}"
   - apply_referral(new_user_id, referral_code) → bool (validate, anti-abuse check)
   - check_and_grant_rewards(referee_id):
     → Called after referee completes onboarding + 5 queries
     → Grant referrer +50 queries; grant referee +50 queries
     → If referrer has 5+ referrals this month → 1 month Plus free
     → If 10+ → 1 month Pro free
   - get_referral_stats(user_id) → code, total/converted referrals, rewards earned

2. Routes: GET /referral/code | POST /referral/apply | GET /referral/stats

3. Frontend (/refer page):
   - Referral code (large, copyable), WhatsApp share, QR code
   - Stats card, monthly leaderboard

4. Anti-abuse:
   Max 20 rewards/month per referrer, phone number verification,
   referee must complete onboarding + 5 real queries,
   same phone cannot be referee twice
```

#### PROMPT C21: Question Paper Generator

```
@agent Build Question Paper Generator for Custom plan users.

1. backend/app/services/question_paper_service.py:
   generate_paper(config: PaperConfig) → QuestionPaper:
   Config: board, class_level, subject, chapters, difficulty_mix,
           question_types (mcq/short/long counts), total_marks,
           duration_minutes, institute_name, institute_logo_url, num_variants (1-3)

   Process:
   a) Query AI Search for questions from specified chapters
   b) GPT-4.1: select questions matching difficulty, generate marking scheme + answer key
   c) Format as PDF: institute header, exam metadata, numbered questions with LaTeX,
      marking scheme, institute branding

   export_pdf(paper) → bytes (WeasyPrint or ReportLab, store in Blob Storage)

2. Routes (Custom plan only — middleware check):
   POST /admin/papers/generate
   GET  /admin/papers
   GET  /admin/papers/{id}/download
```

#### PROMPT C22: Lesson Plan Builder

```
@agent Build Lesson Plan Builder for Custom plan users.

1. backend/app/services/lesson_plan_service.py:
   generate_lesson_plan(config: LessonPlanConfig) → LessonPlan:
   Config: board, class_level, subject, chapter, num_periods, period_duration_mins,
           teaching_style, institute_name

   GPT-4.1 generates:
   - Period-by-period plan (introduction, core concept, examples, activities)
   - Homework assignments and assessment suggestions
   - References to specific textbook pages

   export_pdf(plan) → bytes (with institute branding, store in Blob Storage)

2. Routes (Custom plan only):
   POST /admin/lesson-plans/generate
   GET  /admin/lesson-plans
   GET  /admin/lesson-plans/{id}/download
```

---

#### Daily commands

```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

_End of Javaab Complete Technical Plan V3_
