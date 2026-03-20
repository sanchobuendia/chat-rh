# HR Internal Chatbot API (Secure MVP)

Secure MVP for an internal HR chatbot with:
- FastAPI API
- LangGraph orchestration
- PostgreSQL-backed conversation memory
- Persistent vector store with pgvector
- Separate PostgreSQL for users / permissions / audit / structured salary data
- Async document ingestion pipeline
- Structured salary search with authorization checks

## High-level architecture

- **api**: FastAPI app that serves chat, admin, ingestion, and health endpoints
- **memory_db**: Postgres used by LangGraph checkpointer for thread-scoped memory
- **app_db**: Postgres for users, bases, access control, audit, ingestion jobs, structured payroll
- **vector_db**: Postgres + pgvector for documents, chunks, embeddings, and collection metadata

## Main capabilities in this MVP

1. Chat over HR documents with source citations
2. Per-user access to one or more knowledge bases / collections
3. Structured salary lookup with stricter authorization
4. Upload / register / ingest new files into collections
5. Admin endpoints to create users, bases, and grant / revoke access
6. Conversation memory persisted in PostgreSQL via connection string

## Configuration

The application expects external services through connection strings in `.env`:

```bash
DB_USERS=postgresql://...
DB_HISTORY=postgresql://...
DB_PGVECTOR=postgresql://...
MODEL_PROVIDER=bedrock_converse
bedrock_model_id=us.anthropic.claude-3-5-sonnet-20240620-v1:0
MODEL_TEMPERATURE=0.2
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

`DB_USERS` stores users, grants, payroll and audit data.
`DB_HISTORY` stores LangGraph chat memory.
`DB_PGVECTOR` stores documents, chunks and embeddings.

The chat model is provider-agnostic through `MODEL_PROVIDER` and `BEDROCK_MODEL_ID`. The current default uses Bedrock Converse.

The bootstrap script creates schema, the default knowledge base, seed documents and payroll data. It does not create application users or admins.

For local development, use `scripts/seed_dev_users.py` after the bootstrap if you want sample users and admin access.

## Suggested local run

```bash
cp .env.example .env
make up
make seed
make dev
```

```bash
python scripts/bootstrap_all.py
python scripts/seed_dev_users.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open:
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

## Project layout

```text
app/
  api/
  core/
  db/
  graph/
  models/
  repositories/
  schemas/
  services/
  workers/
seed_data/
sql/
scripts/
```

## Security notes

- Authorization is enforced **before** data reaches the LLM.
- Salary data is queried from structured tables, not from document chunks.
- Collections are filtered by explicit grants in `app_db`.
- Each chat response can be logged in `audit_events`.
- Document metadata supports classification and per-collection access control.

## Current assumptions

- Authentication is represented by a simple header-based stub for the MVP: `X-User-Email`.
- Another team will build the frontend.
- Embeddings default to a deterministic local stub for development, and can be swapped to an external model provider.
- LLM access is configured by provider and model id, with Bedrock as the current default.

## Next production upgrades

- Real SSO / OIDC
- Background queue (Celery / Dramatiq / RQ / cloud queue)
- Object storage for originals
- OCR / advanced parsers
- Reranker model
- Stronger row-level security policies at database level
- Full observability and tracing
