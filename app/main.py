import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from app.config import settings
from app.limiter import limiter
from app.database import engine, Base
from app import models  # registra todos los modelos con Base
from app.routers import auth, usuarios, clientes, productos, cotizaciones

app = FastAPI(title="Sistema de Cotizaciones", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS cotizacion_seq START 1"))
        conn.execute(text("ALTER TABLE productos ADD COLUMN IF NOT EXISTS imagen_url TEXT"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS producto_imagenes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                orden INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS moneda VARCHAR(3) NOT NULL DEFAULT 'MXN'"))
        conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS tipo_cambio NUMERIC(10,4)"))
        conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS empresa VARCHAR(30) NOT NULL DEFAULT 'clm'"))
        # Nuevos campos para clientes
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS atencion_titulo VARCHAR(20)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS atencion_nombre VARCHAR(150)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS estado VARCHAR(100)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS pais VARCHAR(100) DEFAULT 'México'"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS rfc VARCHAR(20)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS domicilio_empresa TEXT"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS domicilio_entrega TEXT"))
        # Actualizar márgenes de usuarios existentes de -10/+10 a -5/+5
        conn.execute(text("UPDATE usuarios SET margen_min = -5.00 WHERE margen_min = -10.00"))
        conn.execute(text("UPDATE usuarios SET margen_max = 5.00 WHERE margen_max = 10.00"))
        conn.commit()

_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── API bajo /api ────────────────────────────────────────────
api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(usuarios.router)
api.include_router(clientes.router)
api.include_router(productos.router)
api.include_router(cotizaciones.router)
app.include_router(api)

# ── Rutas de páginas HTML ────────────────────────────────────
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

def _page(name: str) -> FileResponse:
    return FileResponse(os.path.join(templates_dir, f"{name}.html"))

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")

@app.get("/login", include_in_schema=False)
def page_login():
    return _page("login")

@app.get("/cotizaciones", include_in_schema=False)
def page_cotizaciones():
    return _page("cotizaciones")

@app.get("/clientes", include_in_schema=False)
def page_clientes():
    return _page("clientes")

@app.get("/productos", include_in_schema=False)
def page_productos():
    return _page("productos")

@app.get("/usuarios", include_in_schema=False)
def page_usuarios():
    return _page("usuarios")

# ── Archivos estáticos (css, js, fuentes, etc.) ──────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/", StaticFiles(directory=templates_dir), name="templates")
