# HR AI Chatbot

An intelligent HR assistant deployed on Microsoft Teams, powered by OpenAI and a RAG pipeline over your internal HR documents. Employees can ask questions about policies, benefits, leave, onboarding, and more — and get grounded, accurate answers sourced from your actual HR knowledge base.

---

## Architecture overview

```
Microsoft Teams
      │
      ▼
Bot Framework Adapter (teams_bot.py)
      │
      ▼
FastAPI app (main.py)
      │
      ├── Memory layer        → Redis (multi-turn conversation context)
      ├── RAG pipeline        → Embed query → Vector search → Retrieve chunks
      ├── LLM service         → OpenAI (GPT-4o) with grounded prompt
      ├── PII filter          → Redact before logging, redact before sending
      └── Observability       → LangSmith tracing + token/latency metrics
```

### Key design decisions

- **Async-first** — all services use `async/await`; `AsyncOpenAI` client throughout
- **Conversation memory** — Redis-backed session store preserves multi-turn context per Teams user
- **Typed errors** — `exceptions/errors.py` defines a hierarchy for LLM, retrieval, auth, and PII failures
- **Prompt-as-template** — Jinja2 templates in `prompts/` keep prompts editable without touching Python
- **Semantic caching** — repeated or near-duplicate queries are served from cache, not re-embedded
- **PII protection** — employee data is filtered before it reaches OpenAI and before it's logged

---

## Prerequisites

- Python 3.11+
- Redis 7+ (local or Azure Cache for Redis)
- PostgreSQL with `pgvector` extension **or** Azure AI Search instance
- Azure AD app registration (for Teams bot auth)
- OpenAI API key (GPT-4o recommended)
- Microsoft Teams bot registration (Azure Bot Service)

---

## Local setup

### 1. Clone and install

```bash
git clone path/to/repo
cd hr-ai-chatbot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials — see Environment variables below

# load .env vars
[ ! -f .env ] || export $(grep -v '^#' .env | xargs)
# or this version allows variable substitution and quoted long values
[ -f .env ] && while IFS= read -r line; do [[ $line =~ ^[^#]*= ]] && eval "export $line"; done < .env

```

### 3. Start Redis (Docker)

```bash
docker run -d --name local-redis -p 6379:6379 redis:7-alpine
```

### 4. Set up the vector database

```bash
# pgvector (local Postgres)
docker build -t vectorstore ./infra/docker/vectorstore/Dockerfile
docker run -d --name local-postgres -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -p 5432:5432 vectorstore # run and connect using psql
docker start local-postgres # Run a stopped image
docker exec -it local-postgres bash # connect to running
# psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
# psql -U postgres -c "CREATE TABLE documents (id SERIAL PRIMARY KEY, content TEXT, embedding vector(1536), metadata JSONB);"
# psql -U postgres -c "DELETE from documents;"
# psql -U postgres -c "SELECT count(*) from documents;"

# Create schema
python scripts/init_db.py
```

### 5. Ingest HR documents

```bash
python scripts/ingest_data.py --source ./tests/test_docs --format pdf,docx
# or
python -m scripts.ingest_data --source ./tests/test_docs
```

### 6. Run the app

```bash
bash scripts/run_local.sh
# or:
uvicorn app.main:app --reload --port 8000
```

Use [ngrok](https://ngrok.com/) or [Dev Tunnels](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/) to expose `localhost:8000` for Teams to reach your bot during development.

---

## Environment variables

Copy `.env.example` to `.env` and fill in all values:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Azure Bot Service / Teams
MICROSOFT_APP_ID=
MICROSOFT_APP_PASSWORD=

# Azure AD (for user auth)
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector database (choose one)
VECTOR_STORE=pgvector          # or: azure_ai_search
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hr_bot

# Azure AI Search (if using)
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=hr-documents

# Observability
LANGSMITH_API_KEY=             # optional, enables LangSmith tracing
LANGSMITH_PROJECT=hr-chatbot

# App
APP_ENV=development            # development | staging | production
LOG_LEVEL=INFO
SESSION_TTL_SECONDS=3600
MAX_CONVERSATION_TURNS=20
```

---

## RAG pipeline

The pipeline runs on every user message:

1. **PII filter** — scan and redact sensitive employee data from the query
2. **Cache check** — look up the query in the semantic cache; return cached answer if hit
3. **Embed query** — generate a `text-embedding-3-small` vector for the query
4. **Vector search** — find the top-k relevant document chunks from the knowledge base
5. **Rerank** *(optional)* — apply a cross-encoder reranker for precision improvement
6. **Build prompt** — render the Jinja2 template with context chunks and conversation history
7. **Generate** — call GPT-4o with the grounded prompt
8. **Validate** — run guardrails checks on the response
9. **Cache write** — store result in semantic cache
10. **Return** — send formatted answer back through Teams

---

## Ingesting documents

```bash
# Ingest from a local directory
python scripts/ingest_data.py --source ./hr-docs

# Ingest from SharePoint
python scripts/ingest_data.py --source sharepoint --site "HR Policies" --library "Documents"

# Dry run (no writes)
python scripts/ingest_data.py --source ./hr-docs --dry-run
```

Supported formats: `.pdf`, `.docx`, `.txt`, `.md`

---

## Testing

```bash
# All tests
pytest

# Unit tests only
pytest tests/ -m unit

# Integration tests (requires running Redis + DB)
pytest tests/ -m integration

# Run evaluation harness against golden Q&A pairs
python scripts/evals.py --dataset evals/hr_golden_set.jsonl

python -m pytest --cov-report=xml --cov-report term-missing --cov=app tests/
```

---

## Deployment

### Docker

```bash
docker build -f infra/docker/Dockerfile -t hr-ai-chatbot:latest .
docker run -p 8000:8000 --env-file .env hr-ai-chatbot:latest
```

### Azure Container Apps (recommended)

```bash
az containerapp up \
  --name hr-ai-chatbot \
  --resource-group rg-hr-bot \
  --image hr-ai-chatbot:latest \
  --env-vars @.env
```

### Kubernetes

```bash
kubectl apply -f infra/kubernetes/deployment.yaml
```

---

## Security notes

- All requests from Teams are verified against the Microsoft Bot Framework token
- User identity is resolved from the Teams activity and validated against Azure AD
- PII (names, SSNs, phone numbers, emails) is redacted from queries before they are sent to OpenAI and before they are written to logs
- Conversation history stored in Redis is encrypted at rest (enable Azure Cache for Redis encryption in production)
- No HR document content is returned verbatim to users unless it is explicitly sourced

---

## Contributing

1. Create a feature branch from `main`
2. Add or update tests for your changes
3. Run `pytest` and `ruff check .` before opening a PR
4. PRs require one approval from a team member

---

## License

Internal use only. See `LICENSE` for details.