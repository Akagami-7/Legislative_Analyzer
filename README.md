# AI Legislative Analyzer v1.0 — Citizen's Dashboard

Indian law and parliamentary bills are dense, verbose, and difficult for the average citizen to understand. Running LLMs to summarize these constantly is energy-intensive and environmentally costly. This project provides a "Citizen's Dashboard" that offers real-time, simplified summaries of new government policies and legal documents while minimizing token consumption and carbon footprint.

## The Challenge
- **Document Scale**: Handling documents exceeding 100k tokens.
- **Information Density**: Delivering maximum value per token consumed.
- **Sustainability**: Using Token Compression to shrink legal documents into high-density prompts, reducing energy consumption.

## What v1.0 Does
The AI Legislative Analyzer takes any Indian parliamentary bill as a PDF URL, compresses it intelligently to reduce token consumption, analyzes it using an LLM, and delivers a plain-language summary to citizens — in English or Hindi.

---

## The Full Pipeline — What Happens When You Click Analyze

```
User pastes a PDF URL
        ↓
1. PDF is downloaded automatically
        ↓
2. Text is extracted page by page
   (OCR kicks in if the PDF is a scanned image)
        ↓
3. Document is split into individual sections
   using Indian legal formatting patterns
        ↓
4. BM25 algorithm scores every section
   by civic relevance — penalties, rights,
   consent, obligations score highest
        ↓
5. Low-scoring boilerplate sections are dropped
   (40-70% of sections removed here)
        ↓
6. Remaining sections are compressed —
   top 2-4 sentences extracted per section
        ↓
7. If prompt still too large, auto-trimmed
   to stay under 15,000 token ceiling
        ↓
8. Single Gemini API call on compressed prompt
        ↓
9. Structured JSON returned:
   summary, key changes, affected groups,
   rights impact, implementation date
        ↓
10. CodeCarbon measures real CO₂ emissions
        ↓
11. Translation to Hindi or 9 other
    Indian languages if requested
        ↓
12. Results displayed on citizen dashboard
```

---

## Proven Numbers

| Bill | Original | Compressed | Reduction |
|---|---|---|---|
| DPDP Act 2023 | 14,402 tokens | 4,597 tokens | 68% |
| BNS Act 2023 | 83,617 tokens | 14,952 tokens | 82% |

---

## What the Dashboard Shows

- **Plain-language 3-sentence citizen summary**
- **5 key changes** that affect ordinary people
- **Rights impact** — fundamental rights implications
- **Implementation date**
- **Token efficiency bar** — original vs compressed tokens
- **Compression ratio percentage**
- **Real CO₂ carbon saved** vs naive approach
- **Language selector** — English, Hindi, Telugu, Tamil, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi

---

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env`
3. Get your free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
4. Add your key to `.env`
5. Install dependencies: `pip install -r requirements.txt`
6. Run the application: `python start.py`

> [!NOTE]
> Each team member uses their own free Gemini API key. The free tier allows 15 requests/minute which is sufficient for development.

---

## What v1.0 Does NOT Do (Planned for v2.0)

- No RAG — no retrieval from past bills database
- No vector search — no "similar to IT Act 2000" context
- No clause classification — no penalty/rights tagging
- No readability scoring on individual sections
- No live bill monitoring — manual URL input only
- No user accounts or alert subscriptions
- No impact heatmap of India
- No bill version comparison
- Not publicly hosted — runs locally only
- IndicTrans2 not integrated — uses googletrans
- No Celery async queue — pipeline runs synchronously

---

## For v2.0 Public Hosting

When you host publicly, you have two options:

**Option A — Each user brings their own key**
- User pastes their Gemini API key in the UI
- Your server never stores it
- Zero cost to you
- Slightly worse UX

**Option B — You pay, users don't need a key**
- Your key on the server
- You absorb all API costs
- Need rate limiting per user
- Not feasible for free tier at scale

---

## Where v1.0 Ends

v1.0 ends the moment you run:

```bash
git tag -a v1.0.0 -m "v1.0.0 — Foundation release"
git push origin main --tags
```

At that point the codebase is frozen at this state permanently. Every bill from that point — any Indian parliamentary bill with a PDF URL — can be analyzed, compressed, and explained to citizens in plain language with real carbon metrics.
