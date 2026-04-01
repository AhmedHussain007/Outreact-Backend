from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Generation System API"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    
    SUPABASE_URL: str
    SUPABASE_KEY: str
    N8N_WEBHOOK_URL: str
    N8N_FOLLOWUP_WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
