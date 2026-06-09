from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    port: int
    debug: bool
    database_url: str

    model_config = {"env_file": ".env"}

settings = Settings()