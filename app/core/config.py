from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "hr-internal-chatbot"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    DB_USERS: str
    DB_HISTORY: str
    DB_PGVECTOR: str

    embedding_provider: str = "local"
    embedding_dimension: int = 384
    embedding_model: str = "intfloat/multilingual-e5-small"
    retrieval_query_count: int = 3
    retrieval_top_k_per_query: int = 3
    retrieval_max_distance: float = 0.35
    MODEL_PROVIDER: str = "bedrock_converse"
    BEDROCK_MODEL_ID: str = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    MODEL_TEMPERATURE: float = 0.2

    ingestion_source_dir: str = "/Users/aurelianosancho/Documents/GitHub/UNIFIQUE/RH/seed_data/documents"
    payroll_csv_path: str = "/Users/aurelianosancho/Documents/GitHub/UNIFIQUE/RH/seed_data/payroll/payroll.csv"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
