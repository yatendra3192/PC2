from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:54322/postgres"
    supabase_url: str = "http://localhost:54321"
    supabase_service_key: str = ""
    supabase_anon_key: str = ""
    redis_url: str = "redis://localhost:6379"

    # AI Model Keys — configurable per provider
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"                  # Default model for LLM tasks
    openai_vision_model: str = "gpt-4o"            # Model for vision tasks
    openai_embedding_model: str = "text-embedding-3-small"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    google_vision_api_key: str = ""                # Google Cloud Vision API
    google_document_ai_key: str = ""               # Google Document AI (OCR)

    # Web Scraping
    serpapi_key: str = ""
    scraper_proxy_url: str = ""                    # Optional proxy for scraping

    # External Integrations
    athena_dq_url: str = ""
    athena_dq_api_key: str = ""
    siteone_pim_url: str = ""
    siteone_pim_key: str = ""
    thd_pim_url: str = ""
    thd_pim_key: str = ""

    # App
    demo_mode: bool = False                        # False = use real AI models
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://*.up.railway.app"

    class Config:
        env_file = ".env"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_serpapi(self) -> bool:
        return bool(self.serpapi_key)


settings = Settings()
