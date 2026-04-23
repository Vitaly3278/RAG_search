from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "qwen2.5:7b"
    model_name: str = "gpt-4o-mini"

    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    vector_db_dir: Path = Path("storage/chroma")
    collection_name: str = "company_docs"

    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 4

    telegram_bot_token: str = ""
    session_secret_key: str = "change_me_in_production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
