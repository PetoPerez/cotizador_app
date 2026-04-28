from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    IVA_PORCENTAJE: float = 16.0

    SUPABASE_URL: Optional[str] = None
    SUPABASE_S3_ENDPOINT: Optional[str] = None
    SUPABASE_ACCESS_KEY_ID: Optional[str] = None
    SUPABASE_SECRET_ACCESS_KEY: Optional[str] = None
    SUPABASE_BUCKET: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()