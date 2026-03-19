# Contract Compliance Analyzer

Upload a PDF contract and the system evaluates it against 5 security compliance requirements, returning structured results with compliance state, confidence score, relevant quotes, and rationale. A chat interface allows follow-up questions about the contract.

## Architecture

```
PDF Upload (Streamlit)
    ↓
LlamaParse → Markdown text (PyMuPDF fallback)
    ↓
Chunk (1024 chars) + Embed → FAISS Vector Store
    ↓
For each of 5 compliance questions (parallel):
    Multi-query retrieval → o3-mini → Structured JSON
    ↓
Return results to UI
    ↓
Chat →  RAG  → GPT-4o → Response
```


## Project Structure

```
contract-analyzer/
├── backend/
│   ├── main.py              # FastAPI endpoints
│   ├── parser.py            # PDF parsing (LlamaParse + PyMuPDF fallback)
│   ├── embeddings.py        # Chunking + FAISS vector store
│   ├── analyzer.py          # Compliance analysis (parallel o3-mini calls)
│   ├── chat.py              # Chat with RAG 
│   ├── schemas.py           # Pydantic output schemas
│   ├── constants.py         # Configuration and compliance questions
│   ├── streamlit_app.py     # Streamlit frontend
│   ├── tests/
│   │   └── test_retrieval.py    # Unit tests (no API calls)
│   └── eval/
│       ├── evalRetrieval.py     # LLM-as-judge retrieval eval
│       └── evalFaithfulness.py  # Quote faithfulness eval
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key
- Llamaparse API key

### Local Setup

```bash
git clone <https://github.com/marjandelp/compliance-analyzer.git>
cd contract-analyzer

python -m venv contractAnalyzer
source contractAnalyzer/bin/activate

pip install -r requirements.txt

# macOS only
brew install libmagic
```

Create `.env` file in `backend/`:
```
OPENAI_API_KEY=sk-...
LLAMA_API_KEY=llx-...
```

Run the backend:
```bash
cd backend
uvicorn main:app --reload
```

Run the frontend (new terminal):
```bash
cd backend
streamlit run streamlit_app.py
```

Open `http://localhost:8501`

## Running Tests

```bash
cd backend
pytest tests/test_retrieval.py -v
```

## Running Evaluations

```bash
cd backend
python eval/evalRetrieval.py
python eval/evalFaithfulness.py
```

## Design Decisions

**Dual-model strategy.** o3-mini for compliance analysis because it reasons better across tables and exhibits. GPT-4o for chat where conversational fluency and low latency matter more.

**Multi-query retrieval.** Each compliance question uses 2-4 focused sub-queries instead of one long keyword blob. Single queries dilute embedding similarity — splitting by sub-requirement retrieves from different contract sections and deduplicates results.

**Parallel execution.** All 5 compliance questions analyzed concurrently via `ThreadPoolExecutor`. Reduces total analysis time.

**Separated retrieval queries from analysis questions.** Keyword-rich queries optimized for FAISS embedding search, detailed questions sent to the LLM. Different prompts for different jobs.

**LlamaParse with PyMuPDF fallback.** LlamaParse handles complex contract layouts (tables, multi-column, scanned pages) better than open-source parsers. PyMuPDF fallback ensures parsing still works if LlamaParse is unavailable.

** RAG in chat.**  Prevents irrelevant chunks for broad questions.

**Structured outputs with Pydantic.** Uses `client.beta.chat.completions.parse()` with a Pydantic schema to guarantee valid, typed JSON without manual parsing.

## Edge Cases Handled

- Empty or zero-byte PDFs → rejected before parsing
- Non-PDF files disguised as PDF → rejected via magic byte check
- Password-protected PDFs → rejected with clear error
- Scanned/image-only PDFs → handled via LlamaParse multimodal OCR
- Short documents → bypass RAG, use full text directly
- API timeout/rate limit → retry with exponential backoff (3 attempts)
- Individual question failure → graceful degradation, returns Non-Compliant with error rationale
- Invalid LLM output → Pydantic validators clamp confidence and normalize compliance state
- Prompt injection in chat → input sanitization + system prompt reinforcement

## Evaluation Strategy

**Unit tests** — fast, no API calls, test chunking logic and vector store behavior.

**Retrieval eval (LLM-as-judge)** — verifies retrieved chunks are semantically relevant to each compliance topic. Tested on a security contract (expect 5/5) and an unrelated document (expect 0/5).

**Faithfulness eval** — verifies quotes in compliance results actually appear in the source document, catching hallucinated evidence.

## Cost Estimate (per analysis)

| Service | Calls | Approx Cost |
|---|---|---|
| LlamaParse | 1 | ~$0.003/page |
| o3-mini (analysis) | 5 | ~$0.05-0.08 |
| GPT-4o (chat) | 1-2 per turn | ~$0.004/turn |
| text-embedding-3-small | ~12 | ~$0.001 |
| **Total per upload** | | **~$0.06-0.09** |