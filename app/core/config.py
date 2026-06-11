from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    port: int
    debug: bool
    database_url: str
    admin_secret: str
    qdrant_url: str
    redis_url: str
    openai_api_key: str
    llm_model: str = "gpt-3.5-turbo"

    model_config = {"env_file": ".env"}

settings = Settings()