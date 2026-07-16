"""E2E: vendedor de Servicios de Lavandería (SDL) cotizando equipos de otras empresas.

SDL vende servicios y su catálogo no tiene equipos; el precio de un equipo vive
en producto_empresa (uno por empresa). Por eso, al cotizar un equipo desde SDL el
vendedor indica de qué empresa lo toma (`empresa_origen_id`) y se usa ese precio.

Comprueba:
 1. Vendedor SDL cotiza un equipo de CLM -> usa el precio de CLM.
 2. El mismo equipo con empresa origen Supliese -> usa el precio de Supliese.
 3. Servicio + equipo mezclados en la misma cotización SDL.
 4. Un vendedor NO-SDL no puede usar empresa_origen_id (evita cherry-picking de precios).
 5. Equipo sin empresa origen en SDL -> error claro.
 6. Regresión: un vendedor normal sigue cotizando como siempre.

ESCRIBE EN LA BASE DE DATOS: solo corre contra un Postgres local desechable.

    docker run -d --rm --name cotiz_test -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_DB=cotiz -p 55432:5432 postgres:16-alpine
    python tests/test_sdl_equipos.py
    docker stop cotiz_test
"""
import os
import sys

# Se fija ANTES de importar la app para no heredar el DATABASE_URL del .env, que
# apunta a producción. La guarda de abajo es la red de seguridad.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:55432/cotiz")
os.environ.setdefault("SECRET_KEY", "test-secret-key-para-pruebas-locales")
os.environ.setdefault("ALLOWED_ORIGINS", "*")

# Este test crea usuarios, productos y cotizaciones: jamás debe tocar producción.
if not any(h in os.environ["DATABASE_URL"] for h in ("localhost", "127.0.0.1")):
    sys.exit("ABORTADO: este test escribe en la BD y solo corre contra Postgres local. "
             f"DATABASE_URL apunta a: {os.environ['DATABASE_URL'].split('@')[-1]}")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine
from app import models
from app.security import hash_password

# Paridad con producción: allí la tabla `empresas` se creó con el DDL crudo de
# main.py (id UUID DEFAULT gen_random_uuid()). Si dejamos que create_all() la
# cree, queda sin default de servidor y el INSERT de empresas iniciales falla.
with engine.connect() as c:
    c.execute(text("""
        CREATE TABLE IF NOT EXISTS empresas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            codigo VARCHAR(30) NOT NULL UNIQUE,
            acronimo VARCHAR(10) NOT NULL UNIQUE,
            nombre VARCHAR(200) NOT NULL,
            nombre_corto VARCHAR(50),
            direccion TEXT, rfc VARCHAR(20), telefono VARCHAR(30), email VARCHAR(150),
            logo_url TEXT, logo_decoracion_url TEXT, template_pdf VARCHAR(100),
            activa BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    c.commit()

client = TestClient(app)
client.__enter__()  # dispara on_startup -> crea tablas, migraciones y empresas iniciales


def login(email, password="secret123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def setup():
    db = SessionLocal()
    emp = {e.codigo: e for e in db.query(models.Empresa).all()}
    print("Empresas:", sorted(emp))

    # Producto en CLM ($75,000) y Supliese ($80,000), NO en SDL
    prod = models.Producto(marca="GAMESAIL", equipo="Lavadora", modelo="HS-6028",
                           descripcion="Lavadora 28kg")
    db.add(prod); db.flush()
    db.add(models.ProductoEmpresa(producto_id=prod.id, empresa_id=emp["clm"].id,
                                  precio_lista=75000, activo=True))
    db.add(models.ProductoEmpresa(producto_id=prod.id, empresa_id=emp["supliese"].id,
                                  precio_lista=80000, activo=True))

    svc = models.Servicio(nombre="Lavado industrial", descripcion="Por kg",
                          precio_unitario=500, activo=True)
    db.add(svc)

    cli = models.Cliente(nombre_razon_social="CLIENTE PRUEBA")
    db.add(cli)

    # Vendedor SDL y vendedor CLM
    v_sdl = models.Usuario(nombre="Vendedor SDL", email="sdl@test.com",
                           password_hash=hash_password("secret123"), rol="vendedor",
                           empresa_id=emp["servicios_lavanderia"].id, numero_corto=13,
                           margen_min=-5, margen_max=5, activo=True)
    v_clm = models.Usuario(nombre="Vendedor CLM", email="clm@test.com",
                           password_hash=hash_password("secret123"), rol="vendedor",
                           empresa_id=emp["clm"].id, numero_corto=14,
                           margen_min=-5, margen_max=5, activo=True)
    db.add_all([v_sdl, v_clm])
    db.commit()
    ids = dict(prod=str(prod.id), svc=str(svc.id), cli=str(cli.id),
               clm=str(emp["clm"].id), sup=str(emp["supliese"].id),
               sdl=str(emp["servicios_lavanderia"].id))
    db.close()
    return ids


def crear(headers, empresas, items):
    return client.post("/api/cotizaciones/", headers=headers, json={
        "cliente_id": IDS["cli"], "empresas": empresas, "moneda": "MXN",
        "tipo_cambio": 1, "items": items,
    })


IDS = setup()
h_sdl = login("sdl@test.com")
h_clm = login("clm@test.com")
fallos = []


def check(nombre, cond, detalle=""):
    print(("✅ " if cond else "❌ ") + nombre + ("" if cond else f"  -> {detalle}"))
    if not cond:
        fallos.append(nombre)


# 1) SDL cotiza equipo con precio de CLM
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["clm"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and r.json()[0]["items"][0]["precio_lista"] == 75000.0
check("SDL cotiza equipo de CLM -> precio 75,000", ok, f"{r.status_code} {r.text[:180]}")
if r.status_code == 200:
    check("  numeración con acrónimo SDL", "-SDL-" in r.json()[0]["numero_cotizacion"],
          r.json()[0]["numero_cotizacion"])
    check("  guarda empresa_origen_id", r.json()[0]["items"][0]["empresa_origen_id"] == IDS["clm"])

# 2) Mismo equipo, precio de Supliese
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and r.json()[0]["items"][0]["precio_lista"] == 80000.0
check("SDL cotiza mismo equipo desde Supliese -> precio 80,000", ok, f"{r.status_code} {r.text[:180]}")

# 3) Mezclar servicio + equipo
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"servicio_id": IDS["svc"], "cantidad": 2, "porcentaje_ajuste": 0},
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["clm"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and len(r.json()[0]["items"]) == 2
sub = r.json()[0]["subtotal"] if r.status_code == 200 else None
check("SDL mezcla servicio + equipo en una cotización", ok, f"{r.status_code} {r.text[:180]}")
check("  subtotal = 2x500 + 75,000 = 76,000", sub == 76000.0, str(sub))

# 4) Vendedor NO-SDL no puede escoger empresa de origen (guarda de seguridad)
r = crear(h_clm, ["clm"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
check("Vendedor CLM NO puede usar empresa_origen_id (evita cherry-picking de precios)",
      r.status_code == 400, f"{r.status_code} {r.text[:180]}")

# 5) Equipo en SDL sin empresa origen -> error claro
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "cantidad": 1, "porcentaje_ajuste": 0}])
check("Equipo en SDL sin empresa origen -> 400 con mensaje claro",
      r.status_code == 400, f"{r.status_code} {r.text[:180]}")
if r.status_code == 400:
    print("     mensaje:", r.json().get("detail"))

# 6) El vendedor CLM sigue cotizando normal
r = crear(h_clm, ["clm"], [{"producto_id": IDS["prod"], "cantidad": 1, "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and r.json()[0]["items"][0]["precio_lista"] == 75000.0
check("Regresión: vendedor CLM cotiza normal -> 75,000", ok, f"{r.status_code} {r.text[:180]}")

print()
sys.exit(1 if fallos else 0)
