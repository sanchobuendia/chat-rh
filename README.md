# 🤖 Chat RH

<p align="center">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-API-0f766e?style=for-the-badge&logo=fastapi&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-Orchestration-1d4ed8?style=for-the-badge">
  <img alt="pgvector" src="https://img.shields.io/badge/pgvector-Vector%20Search-7c3aed?style=for-the-badge">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-App%20%2B%20Memory-1e40af?style=for-the-badge&logo=postgresql&logoColor=white">
  <img alt="Sentence Transformers" src="https://img.shields.io/badge/SentenceTransformers-Local%20Embeddings-b45309?style=for-the-badge">
</p>

<p align="center">
  API de chatbot interno de RH com controle de acesso por base, busca vetorial com <code>pgvector</code>, memória de conversa, ingestão de documentos e consulta estruturada de folha salarial.
</p>

---

## 🔥 Visão Geral

O projeto expõe uma API FastAPI para:

- responder perguntas sobre documentos de RH com citações;
- controlar acesso do usuário às bases de conhecimento;
- consultar dados salariais com regras mais rígidas de autorização;
- ingerir documentos e gerar embeddings;
- manter memória de conversa por `thread_id`.

## ✅ Principais Capacidades

- `Chat RAG` com geração de consultas, recuperação vetorial e resposta final via LLM.
- `Payroll lookup` estruturado, sem depender do conteúdo dos chunks.
- `Admin API` para criar usuários, bases e conceder ou revogar acesso.
- `Bootstrap` de schema, base padrão, documentos seed e CSV de folha.
- `Embeddings locais` com `sentence-transformers`.
- `Threshold de relevância` para reduzir respostas com contexto fraco.

## 📊 Arquitetura

```text
Cliente
  |
  v
FastAPI
  |
  +--> Auth stub por header (X-User-Email)
  +--> ChatService
         |
         +--> RouterService -> define rota: rag | payroll | smalltalk
         +--> RetrievalService -> embeddings + pgvector similarity search
         +--> PayrollService -> consulta estruturada em DB_USERS
         +--> LLMService -> resposta final
  |
  +--> Admin / Ingestion / Payroll endpoints

DB_USERS
  users, knowledge_bases, user_base_access, audit_events, payroll_records, ingestion_jobs

DB_HISTORY
  memória de conversa do LangGraph / checkpointer

DB_PGVECTOR
  documents, chunks, embeddings
```

## 🐍 Stack

- `FastAPI` para a API HTTP
- `LangGraph` para orquestração do fluxo de chat
- `PostgreSQL` para app data e memória
- `pgvector` para busca vetorial
- `sentence-transformers` para embeddings locais
- `Bedrock Converse` como modelo default de chat

## 📁 Estrutura do Projeto

```text
app/
  api/            rotas e dependências HTTP
  core/           config e logging
  db/             sessões SQLAlchemy
  graph/          definição do fluxo LangGraph
  models/         modelos SQLAlchemy
  repositories/   acesso a dados
  schemas/        modelos Pydantic
  services/       regras de negócio
  workers/        bootstrap utilitário
docs/
  API_EXAMPLES.md
scripts/
  bootstrap_all.py
  seed_dev_users.py
seed_data/
  documents/
  payroll/
sql/
tests/
```

## 🤖 Fluxo de Chat

1. O cliente envia uma pergunta para `POST /api/v1/chat`.
2. O usuário é identificado pelo header `X-User-Email`.
3. O `RouterService` decide a rota:
   - `rag`
   - `payroll`
   - `smalltalk`
4. Em `rag`, o sistema:
   - gera queries de busca;
   - calcula embeddings;
   - consulta o `pgvector`;
   - aplica `retrieval_max_distance`;
   - deduplica os chunks;
   - envia os resultados ao LLM.
5. A resposta volta com citações e metadados de relevância.

## 📊 Embeddings e Busca Vetorial

### 🔥 Como está configurado hoje

- provider local com `sentence-transformers`;
- modelo default: `intfloat/multilingual-e5-small`;
- dimensão default: `384`;
- busca vetorial com operador `<=>` do `pgvector`;
- filtro por distância máxima via `retrieval_max_distance`.

### ⚠️ Observações importantes

- o modelo de embedding é carregado uma vez por processo e reutilizado entre requests;
- mudar modelo, provider ou dimensão exige reindexação da base vetorial;
- se nenhum chunk passar no threshold, o sistema segue sem contexto em vez de forçar um RAG fraco.

## 🔗 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto.

### ✅ Obrigatórias

```env
DB_USERS=postgresql://...
DB_HISTORY=postgresql://...
DB_PGVECTOR=postgresql://...
```

### 🤖 App / Chat

```env
APP_NAME=hr-internal-chatbot
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

MODEL_PROVIDER=bedrock_converse
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20240620-v1:0
MODEL_TEMPERATURE=0.2
```

### 📊 Embeddings / Retrieval

```env
embedding_provider=local
embedding_model=intfloat/multilingual-e5-small
embedding_dimension=384
retrieval_query_count=3
retrieval_top_k_per_query=3
retrieval_max_distance=0.35
```

### 🔗 Bedrock Embeddings

Se optar por embeddings no Bedrock:

```env
embedding_provider=bedrock
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

### 🔗 OpenAI Embeddings

Se optar por embeddings via OpenAI:

```env
embedding_provider=openai
embedding_model=text-embedding-3-small
OPENAI_API_KEY=...
```

### 📁 Seeds locais

```env
ingestion_source_dir=/caminho/para/seed_data/documents
payroll_csv_path=/caminho/para/seed_data/payroll/payroll.csv
```

## 🐍 Instalação

### 🐍 Ambiente Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 🤖 Rodando a API localmente

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 🔗 Usando Docker Compose

```bash
make up
```

O `docker-compose.yml` sobe o serviço `api` com reload e monta o diretório do projeto em `/app`.

## 🔥 Bootstrap e Seed

O projeto inclui dois scripts principais:

- `scripts/bootstrap_all.py`
- `scripts/seed_dev_users.py`

### ✅ O que o bootstrap faz

- cria e valida schema em `DB_USERS`;
- garante extensão `vector` em `DB_PGVECTOR`;
- cria schema vetorial;
- garante a base default `rh-geral`;
- ingere os documentos de `seed_data/documents`;
- importa a folha de `seed_data/payroll/payroll.csv`.

### 💡 Execução sugerida

```bash
python scripts/bootstrap_all.py
python scripts/seed_dev_users.py
```

### 💡 Usuários seed de desenvolvimento

O script de seed cria usuários de exemplo e concede acesso à base `rh-geral`.

## 🔗 Endpoints

### ✅ Health

- `GET /api/v1/health`

### 🤖 Chat

- `POST /api/v1/chat`

### 📊 Payroll

- `GET /api/v1/payroll/employee`

### 🤖 Admin Users

- `POST /api/v1/admin/users`
- `GET /api/v1/admin/users`
- `DELETE /api/v1/admin/users/{user_id}`

### 📁 Admin Bases

- `POST /api/v1/admin/bases`
- `GET /api/v1/admin/bases`
- `POST /api/v1/admin/bases/grant`
- `POST /api/v1/admin/bases/revoke`

### 📁 Ingestion

- `POST /api/v1/ingestion/upload`
- `POST /api/v1/ingestion/seed`

💡 Mais exemplos estão em [docs/API_EXAMPLES.md](/Users/aurelianosancho/Documents/GitHub/UNIFIQUE/chat-rh/docs/API_EXAMPLES.md).

## 💡 Exemplo de Uso

### 🤖 Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'X-User-Email: joao@empresa.com' \
  -d '{"thread_id":"t-1","question":"Como funciona a política de férias?"}'
```

### ✅ Create user

```bash
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H 'Content-Type: application/json' \
  -H 'X-User-Email: ana@empresa.com' \
  -d '{"email":"nova@empresa.com","full_name":"Nova Pessoa","role":"employee","department":"RH","is_manager":false}'
```

## ⚠️ Segurança e Restrições

- o MVP usa autenticação por header: `X-User-Email`;
- autorização é aplicada antes de enviar contexto ao LLM;
- folha salarial é tratada por consulta estruturada;
- o acesso às bases é controlado em `user_base_access`;
- eventos de chat e payroll podem ser auditados.

## ✅ Testes

Rodar a suíte:

```bash
pytest -q
```

Rodar com coverage:

```bash
python -m coverage run -m pytest
python -m coverage report -m
```

## 🔥 Operação e Manutenção

### ⚠️ Quando reindexar documentos

Reingira a base vetorial se mudar:

- `embedding_provider`
- `embedding_model`
- `embedding_dimension`
- `BEDROCK_EMBEDDING_MODEL_ID`

### ✅ Quando não precisa reindexar

Não precisa recriar embeddings se mudar apenas:

- `retrieval_query_count`
- `retrieval_top_k_per_query`
- `retrieval_max_distance`

## 💡 Comandos Úteis

```bash
make up      # sobe a API via docker compose
make down    # derruba containers e volumes
make seed    # roda bootstrap dentro do container api
make dev     # sobe uvicorn local com reload
make test    # roda pytest -q
```

## ⚠️ Limitações Atuais

- autenticação ainda é stubada por header;
- não há fila assíncrona real para ingestão;
- não há reranker;
- não há object storage para originais;
- observabilidade ainda é básica;
- o frontend não faz parte deste repositório.

## 🔥 Próximos Passos Sugeridos

- integrar SSO/OIDC;
- adicionar reranking;
- incluir background jobs para ingestão;
- ampliar observabilidade e tracing;
- revisar políticas de segurança e governança de dados;
- endurecer estratégia de produção para embeddings e memória.
