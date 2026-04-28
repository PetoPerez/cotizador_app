import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.database import engine, Base
from app import models  # registra todos los modelos con Base
from app.routers import auth, usuarios, clientes, productos, cotizaciones

app = FastAPI(title="Sistema de Cotizaciones", version="1.0.0")


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
        conn.commit()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.mount("/", StaticFiles(directory=templates_dir), name="static")
