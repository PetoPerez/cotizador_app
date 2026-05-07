from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    IVA_PORCENTAJE: float = 16.0

    # Orígenes permitidos en CORS, separados por coma.
    # En Railway ponlo como: https://tu-app.railway.app
    ALLOWED_ORIGINS: str = "*"

    # Datos de la empresa para el PDF de cotización
    EMPRESA_NOMBRE: str = "Tu Empresa S.A. de C.V."
    EMPRESA_MARCA: str = "CLM"          # texto del logo y marca de agua
    EMPRESA_NOMBRE_CORTO: str = "EMPRESA"
    EMPRESA_DIRECCION: str = "Calle, Col., Ciudad, C.P. XXXXX"
    EMPRESA_TELEFONO: str = "(33) 0000-0000"
    EMPRESA_EMAIL: str = "contacto@empresa.com"

    SUPABASE_URL: Optional[str] = None
    SUPABASE_S3_ENDPOINT: Optional[str] = None
    SUPABASE_ACCESS_KEY_ID: Optional[str] = None
    SUPABASE_SECRET_ACCESS_KEY: Optional[str] = None
    SUPABASE_BUCKET: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()