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
from app.routers import auth, usuarios, clientes, productos, cotizaciones, empresas

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
        # Renombrar empresa supliese_gomez → servicios_lavanderia
        conn.execute(text("UPDATE cotizaciones SET empresa = 'servicios_lavanderia' WHERE empresa = 'supliese_gomez'"))
        # Permitir nuevo rol 'servicios' en check constraint
        conn.execute(text("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check"))
        conn.execute(text("ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check CHECK (rol IN ('admin', 'vendedor', 'servicios'))"))

        # ── Fase 1: Tabla empresas + tabla puente producto_empresa ──
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS empresas (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                codigo VARCHAR(30) NOT NULL UNIQUE,
                acronimo VARCHAR(10) NOT NULL UNIQUE,
                nombre VARCHAR(200) NOT NULL,
                nombre_corto VARCHAR(50),
                direccion TEXT,
                rfc VARCHAR(20),
                telefono VARCHAR(30),
                email VARCHAR(150),
                logo_url TEXT,
                logo_decoracion_url TEXT,
                template_pdf VARCHAR(100),
                activa BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS producto_empresa (
                producto_id UUID NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                empresa_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                precio_lista NUMERIC(12,2) NOT NULL,
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (producto_id, empresa_id)
            )
        """))

        # Insertar las 4 empresas iniciales (idempotente)
        _empresas_iniciales = [
            ('clm',                 'CLM', 'CLM',                    'CLM',                    'images/clm.jpeg',                'images/clm_r.jpeg',     'cotizacion_clm.html'),
            ('supliese_gamesail',   'GS',  'Gamesail',               'Gamesail',               'images/supliese_gamesail.jpeg',  'images/gamesail_r.jpeg','cotizacion_supliese_gamesail.html'),
            ('supliese',            'SUP', 'Supliese',               'Supliese',               'images/supliese.jpeg',           'images/supliese_r.jpeg','cotizacion_supliese.html'),
            ('servicios_lavanderia','SDL', 'Servicios de Lavandería','SDL',                    'images/supliese.jpeg',           None,                    'cotizacion_servicios_lavanderia.html'),
        ]
        for codigo, acronimo, nombre, nombre_corto, logo_url, logo_deco, tpl in _empresas_iniciales:
            conn.execute(text("""
                INSERT INTO empresas (codigo, acronimo, nombre, nombre_corto, direccion, rfc, telefono, email,
                                      logo_url, logo_decoracion_url, template_pdf)
                VALUES (:codigo, :acronimo, :nombre, :nombre_corto, :direccion, :rfc, :telefono, :email,
                        :logo_url, :logo_deco, :tpl)
                ON CONFLICT (codigo) DO NOTHING
            """), {
                "codigo": codigo, "acronimo": acronimo, "nombre": nombre, "nombre_corto": nombre_corto,
                "direccion": settings.EMPRESA_DIRECCION,
                "rfc": "SGO210826M44",
                "telefono": settings.EMPRESA_TELEFONO,
                "email": settings.EMPRESA_EMAIL,
                "logo_url": logo_url, "logo_deco": logo_deco, "tpl": tpl,
            })

        # ── Fase 2: columnas multi-empresa en usuarios y cotizaciones ──
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id)"))
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS numero_corto INT UNIQUE"))
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cotizaciones_count INT NOT NULL DEFAULT 0"))
        conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id)"))

        # Backfill productos → producto_empresa (solo productos que aún no tienen ninguna empresa)
        conn.execute(text("""
            INSERT INTO producto_empresa (producto_id, empresa_id, precio_lista, activo)
            SELECT p.id, e.id, p.precio_lista, p.activo
            FROM productos p
            CROSS JOIN empresas e
            WHERE e.codigo IN ('clm', 'supliese_gamesail', 'supliese')
              AND NOT EXISTS (SELECT 1 FROM producto_empresa pe WHERE pe.producto_id = p.id)
        """))

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
api.include_router(empresas.router)
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
