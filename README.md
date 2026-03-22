# Legislative Analyzer

Indian law is not written for citizens. The Bharatiya Nyaya Sanhita runs 438 sections
across 83,000 tokens. Nobody reads it. We built something that does.

---

## The Problem We Solved

Parliamentary bills in India are published as gazette PDFs — dense, bilingual,
inconsistently formatted, and often scanned. Before any summarization can happen,
you need to actually get the text out cleanly. That turned out to be the hard part.

The compression and summarization side has a separate challenge: most bills exceed
what any LLM can process in one shot. The BNS 2023 at 83k tokens is nearly 6x
the context of a typical free-tier model. We needed to cut it down intelligently,
not randomly. And we needed to do it in a way that didn't waste tokens sending
the same boilerplate to an expensive API on every request.

That's where ScaleDown came in.

---

## What ScaleDown Did For Us

ScaleDown is the second compression pass that runs after our BM25+TF-IDF ranking
drops the low-relevance sections. By the time a bill reaches ScaleDown, it's already
been cut to the most civically relevant content. ScaleDown then compresses that
further at the sentence level — keeping key legal terms, removing redundant
sub-clauses, and tightening the prose without losing meaning.

The practical impact:

| Bill | After BM25 | After ScaleDown | Total Reduction |
|------|------------|-----------------|-----------------|
| DPDP Act 2023 | 7,200 tokens | 4,597 tokens | 68% from original |
| BNS Act 2023 | 18,000 tokens | 8,151 tokens | 90% from original |

Without ScaleDown, the BNS Act would still exceed the 15,000 token ceiling after
BM25 filtering alone. ScaleDown is what makes 90% compression possible while
keeping the summary coherent. It also directly reduces API costs and CO2 emissions
per bill processed — the two metrics this project is being judged on.

---

## Full Pipeline
```
Gazette PDF URL
  → 6-level fallback scraper
  → pdfplumber + PyMuPDF text extraction
  → Tesseract OCR if scanned
  → Indian legal regex section splitting
  → spaCy + custom NER
  → Flesch readability scoring per section
        |
        v
  → BM25 + TF-IDF civic relevance ranking
  → Low-relevance sections dropped
  → Semantic chunking (sentence-transformers)
  → Extractive compression per section
  → ScaleDown second-pass compression
  → RAG context injection (ChromaDB, 15 bills indexed)
  → Token ceiling check (15k max)
        |
        v
  → Single LLM call (Gemini / Groq / OpenRouter / Claude / GPT / Ollama)
  → Structured JSON response parsed
  → IndicTrans2 translation (22 Indian languages)
  → Citizen dashboard display
```

---

## Compression Results

| Bill | Original | After BM25 | After ScaleDown | Final Cut |
|------|----------|------------|-----------------|-----------|
| DPDP Act 2023 | 14,402 tokens | ~7,200 tokens | 4,597 tokens | 68% |
| BNS Act 2023 | 83,617 tokens | ~18,000 tokens | 8,151 tokens | 90% |

The two-pass approach is what makes large bills tractable. BM25 handles coarse
relevance filtering at the section level. ScaleDown handles fine-grained compression
at the sentence level. Together they bring even the largest Indian Acts inside the
LLM context window without losing the civic substance.

---

## Team

| Who | Branch | What they own |
|-----|--------|---------------|
| Suhas (Akagami) | `Akagami` | Compression, BM25+TF-IDF, ScaleDown integration, RAG, LLM routing, translation, carbon tracking |
| Rishi | `rishi` | Ingestion, OCR, scraper, section splitting, NER, readability scoring |
| AkashSamuel | `AkashSamuel` | FastAPI backend, citizen dashboard |

Nobody pushes to `main` or `dev` directly. Everything goes through PRs.
Akagami merges to main per version tag.

---

## LLM Support

Model lists are fetched dynamically from each provider — nothing hardcoded.

| Provider | Free models available |
|----------|-----------------------|
| Gemini | gemini-2.0-flash, gemini-2.5-flash, gemini-3.1-flash |
| Groq | llama-3.3-70b, openai/gpt-oss-120b, kimi-k2-instruct |
| OpenRouter | llama-3.2, mistral, deepseek-v3, deepseek-r1, qwen-2.5, gemma-2, command-r |
| OpenAI | gpt-5.4-nano, gpt-4.1-nano (tier dependent) |
| Claude | claude-3.5-sonnet (paid), claude-3-haiku (paid) |
| Ollama | any locally installed model |

---

## Pre-Ingested Bills (ChromaDB)

15 acts indexed for RAG context retrieval:

| Bill | Sections | Tokens |
|------|----------|--------|
| Bharatiya Nyaya Sanhita 2023 | 438 | 83,617 |
| Bharatiya Nagarik Suraksha 2023 | 124 | 85,000 |
| Land Acquisition Act 2013 | 91 | 31,006 |
| National Medical Commission 2019 | 68 | 22,000 |
| IT Act 2000 | 66 | 35,000 |
| Right to Education Act 2009 | 76 | 20,000 |
| Telecommunications Act 2023 | 76 | 28,000 |
| Jan Vishwas Act 2023 | 44 | 18,000 |
| RTI Act 2005 | 41 | 25,000 |
| Consumer Protection Act 2019 | 36 | 30,000 |
| Competition Act 2002 | 24 | 22,000 |
| Code on Wages 2019 | 20 | 18,000 |
| Forest Rights Act 2006 | 19 | 15,000 |
| Persons with Disabilities Act 2016 | 19 | 20,000 |
| Environment Protection Act 1986 | 15 | 12,000 |

---

## Setup

Python 3.10+, Tesseract OCR, Poppler, Chrome required.
```bash
git clone https://github.com/Akagami-7/Legislative_Analyzer.git
cd Legislative_Analyzer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Windows:
```bash
winget install tesseract-ocr.tesseract
winget install poppler
```

Copy `.env.example` to `.env`:
```
GEMINI_API_KEY=
HUGGINGFACE_TOKEN=       # optional, for IndicTrans2
SCALEDOWN_API_KEY=       # required for second-pass compression
```

Free Gemini key: https://aistudio.google.com/app/apikey
ScaleDown API: https://scaledown.dev

---

## Running
```bash
python start.py
```

API at http://localhost:8000/docs and dashboard at http://localhost:3000.

Or run separately:
```bash
python -m uvicorn src.api.main:app --reload --port 8000
cd frontend && python -m http.server 3000
```

---

## API
```bash
# Submit a bill for analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://egazette.gov.in/WriteReadData/2023/247654.pdf",
    "language": "hi",
    "llm_provider": "gemini",
    "llm_api_key": "your_key",
    "llm_model": "gemini-2.0-flash"
  }'

# Get result
curl http://localhost:8000/api/v1/bills/{task_id}

# List available models for a provider
curl "http://localhost:8000/api/v1/models/gemini?api_key=your_key"
```

---

## Project Layout
```
Legislative_Analyzer/
├── src/
│   ├── shared_schemas.py
│   ├── ingestion/
│   │   ├── pdf_parser.py
│   │   ├── ocr_engine.py
│   │   ├── scraper.py
│   │   ├── section_splitter.py
│   │   ├── ner_pipeline.py
│   │   ├── readability.py
│   │   └── gazette_monitor.py
│   ├── compression/
│   │   ├── bm25_ranker.py
│   │   ├── semantic_chunker.py
│   │   ├── extractor.py
│   │   ├── prompt_assembler.py
│   │   ├── llm_client.py
│   │   ├── multi_llm_client.py
│   │   ├── rag_embedder.py
│   │   ├── rag_retriever.py
│   │   ├── scaledown_client.py
│   │   ├── translator.py
│   │   └── token_logger.py
│   └── api/
│       ├── main.py
│       ├── routes/
│       │   ├── analyze.py
│       │   ├── bills.py
│       │   └── models.py
│       └── services/
│           └── real_pipeline.py
├── frontend/
│   └── index.html
├── ingested_bills/
├── chroma_db/
├── tests/
├── batch_ingest.py
├── generate_json.py
├── run_pipeline.py
├── start.py
├── diagnose.py
├── find_url.py
├── test_translation.py
├── .env.example
└── requirements.txt
```

---

## Tests
```bash
pytest tests/ -v
```

Tests run against real PDF files. No mocked data. Covers parsing, section detection,
NER deduplication, schema contracts, and compression ratios.

---

## Known Issues

- Land Acquisition Act 2013 ingested via OCR — section quality varies.
- IndicTrans2 needs 2-3GB RAM. Falls back to Google Translate automatically.
- 6 bills have sparse section counts due to gazette wrapper PDF formatting.
- ScaleDown requires an active API key — without it the pipeline falls back
  to BM25-only compression which may exceed the 15k token ceiling on large bills.
- Ollama requires local setup and is not available on any hosted demo.

---

## Releases

- v1.0.0 — ingestion pipeline, BM25 compression, Gemini, Hindi output
- v2.0.0 — ScaleDown second-pass compression, RAG via ChromaDB, semantic chunking,
           multi-LLM routing, IndicTrans2, TF-IDF combined with BM25

---

## License

MIT  check this out