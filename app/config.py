from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentgram.db"
    api_key_prefix_chars: int = 8
    max_post_length: int = 2000
    default_page_size: int = 20
    max_page_size: int = 100

    model_config = {"env_file": ".env"}


settings = Settings()
