import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DB_USERS", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("DB_HISTORY", "postgresql://user:pass@localhost/history")
os.environ.setdefault("DB_PGVECTOR", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("MODEL_PROVIDER", "bedrock_converse")
os.environ.setdefault("BEDROCK_MODEL_ID", "fake-model")
os.environ.setdefault("MODEL_TEMPERATURE", "0.2")
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("EMBEDDING_DIMENSION", "8")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")
