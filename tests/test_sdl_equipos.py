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

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models
from app.security import hash_password

# Arranca contra una BD vacía: on_startup crea las tablas, corre las migraciones
# idempotentes y siembra las empresas iniciales. (Los modelos definen
# server_default para las PKs UUID y para empresas.activa, así que create_all
# genera esos valores y el seed de empresas funciona en una BD nueva.)
client = TestClient(app)
client.__enter__()


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


def crear(headers, empresas, items, moneda="MXN", tc=1):
    return client.post("/api/cotizaciones/", headers=headers, json={
        "cliente_id": IDS["cli"], "empresas": empresas, "moneda": moneda,
        "tipo_cambio": tc, "items": items,
    })


IDS = setup()
h_sdl = login("sdl@test.com")
h_clm = login("clm@test.com")
fallos = []


def check(nombre, cond, detalle=""):
    print(("✅ " if cond else "❌ ") + nombre + ("" if cond else f"  -> {detalle}"))
    if not cond:
        fallos.append(nombre)


# Supliese = 80,000 USD ; CLM = 75,000 USD (mismo equipo, distinto precio)
SUP_USD = 80000.0

# 1) SDL cotiza equipo desde Supliese (única empresa origen permitida)
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and r.json()[0]["items"][0]["precio_lista"] == SUP_USD
check("SDL cotiza equipo desde Supliese -> precio 80,000", ok, f"{r.status_code} {r.text[:180]}")
if r.status_code == 200:
    check("  numeración con acrónimo SDL", "-SDL-" in r.json()[0]["numero_cotizacion"],
          r.json()[0]["numero_cotizacion"])
    check("  guarda empresa_origen_id (Supliese)",
          r.json()[0]["items"][0]["empresa_origen_id"] == IDS["sup"])

# 2) Equipo desde otra empresa (CLM) en SDL -> rechazado (solo Supliese)
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["clm"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
check("SDL: equipo desde CLM -> 400 (solo Supliese)", r.status_code == 400,
      f"{r.status_code} {r.text[:180]}")
if r.status_code == 400:
    print("     mensaje:", r.json().get("detail"))

# 3) Mezclar servicio + equipo (Supliese)
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"servicio_id": IDS["svc"], "cantidad": 2, "porcentaje_ajuste": 0},
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0}])
ok = r.status_code == 200 and len(r.json()[0]["items"]) == 2
sub = r.json()[0]["subtotal"] if r.status_code == 200 else None
check("SDL mezcla servicio + equipo en una cotización", ok, f"{r.status_code} {r.text[:180]}")
check("  subtotal = 2x500 + 80,000 = 81,000", sub == 81000.0, str(sub))

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

# 6) El vendedor CLM sigue cotizando normal (precio USD sin convertir)
r = crear(h_clm, ["clm"], [{"producto_id": IDS["prod"], "cantidad": 1, "porcentaje_ajuste": 0}],
          tc=18)
ok = r.status_code == 200 and r.json()[0]["items"][0]["precio_lista"] == 75000.0
check("Regresión: cotización CLM guarda el equipo en USD (75,000, sin convertir)", ok,
      f"{r.status_code} {r.text[:180]}")

# 7) MONEDA: equipo Supliese (USD) en cotización SDL se normaliza USD->MXN.
#    80,000 USD con tc=18 debe guardarse como 1,440,000 MXN.
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0}], tc=18)
precio = r.json()[0]["items"][0]["precio_lista"] if r.status_code == 200 else None
check("SDL: equipo USD 80,000 con tc=18 se guarda en MXN (1,440,000)",
      precio == SUP_USD * 18, f"got {precio}")

# 8) Servicio (ya en MXN) NO se convierte; equipo sí.
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1,
     "porcentaje_ajuste": 0},
    {"servicio_id": IDS["svc"], "cantidad": 1, "porcentaje_ajuste": 0}], tc=18)
if r.status_code == 200:
    its = {("svc" if i["servicio_id"] else "eq"): i for i in r.json()[0]["items"]}
    check("SDL mixto: servicio en MXN (500) y equipo convertido (1,440,000)",
          its["svc"]["precio_lista"] == 500.0 and its["eq"]["precio_lista"] == SUP_USD * 18,
          str({k: v["precio_lista"] for k, v in its.items()}))
    check("  subtotal mixto = 1,440,500",
          r.json()[0]["subtotal"] == 500 + SUP_USD * 18, str(r.json()[0]["subtotal"]))
else:
    check("SDL mixto con tc=18", False, r.text[:180])

# 9) MONEDA DEFAULT: una cotización sin campo 'moneda' se guarda en USD.
r = client.post("/api/cotizaciones/", headers=h_clm, json={
    "cliente_id": IDS["cli"], "empresas": ["clm"], "tipo_cambio": 18,
    "items": [{"producto_id": IDS["prod"], "cantidad": 1, "porcentaje_ajuste": 0}]})
check("Default: cotización sin 'moneda' se guarda en USD",
      r.status_code == 200 and r.json()[0]["moneda"] == "USD",
      f"{r.status_code} {r.text[:120]}")

# 10) SERVICIO ADICIONAL en SDL, cotización en MXN: precio se guarda tal cual.
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"descripcion_libre": "Flete a Guadalajara", "precio_unitario": 3500, "cantidad": 1,
     "porcentaje_ajuste": 0}], moneda="MXN", tc=18)
if r.status_code == 200:
    it = r.json()[0]["items"][0]
    check("SDL adicional (MXN): guarda descripción y precio 3,500",
          it["descripcion_libre"] == "Flete a Guadalajara" and it["precio_lista"] == 3500.0
          and it["producto_id"] is None and it["servicio_id"] is None,
          str(it))
else:
    check("SDL adicional (MXN)", False, r.text[:180])

# 11) SERVICIO ADICIONAL en SDL, cotización en USD: se normaliza USD->MXN (x tc).
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"descripcion_libre": "Maniobras", "precio_unitario": 100, "cantidad": 2,
     "porcentaje_ajuste": 0}], moneda="USD", tc=18)
if r.status_code == 200:
    it = r.json()[0]["items"][0]
    check("SDL adicional (USD 100, tc=18): se guarda en MXN (1,800) e importe 3,600",
          it["precio_lista"] == 1800.0 and it["importe"] == 3600.0, str(it))
else:
    check("SDL adicional (USD)", False, r.text[:180])

# 12) Mezcla servicio + equipo + adicional en una sola cotización SDL.
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"servicio_id": IDS["svc"], "cantidad": 1, "porcentaje_ajuste": 0},
    {"producto_id": IDS["prod"], "empresa_origen_id": IDS["sup"], "cantidad": 1, "porcentaje_ajuste": 0},
    {"descripcion_libre": "Flete", "precio_unitario": 2000, "cantidad": 1, "porcentaje_ajuste": 0},
], moneda="MXN", tc=18)
check("SDL: servicio + equipo + adicional en una cotización (3 ítems)",
      r.status_code == 200 and len(r.json()[0]["items"]) == 3, f"{r.status_code} {r.text[:180]}")

# 13) Servicio adicional (flete) SÍ permitido fuera de SDL (cotización CLM en USD).
#     500 capturado en USD queda tal cual (base USD). El servicio (MXN) se convierte.
r = crear(h_clm, ["clm"], [
    {"producto_id": IDS["prod"], "cantidad": 1, "porcentaje_ajuste": 0},
    {"servicio_id": IDS["svc"], "cantidad": 1, "porcentaje_ajuste": 0},
    {"descripcion_libre": "Flete", "precio_unitario": 500, "cantidad": 1, "porcentaje_ajuste": 0}],
    moneda="USD", tc=18)
if r.status_code == 200:
    its = {("prod" if i["producto_id"] else "svc" if i["servicio_id"] else "flete"): i
           for i in r.json()[0]["items"]}
    check("CLM (USD) admite producto + servicio + flete",
          len(its) == 3 and its["flete"]["precio_lista"] == 500.0
          and round(its["svc"]["precio_lista"], 2) == round(500.0 / 18, 2),  # svc 500 MXN -> USD
          str({k: v["precio_lista"] for k, v in its.items()}))
else:
    check("CLM admite producto + servicio + flete", False, f"{r.status_code} {r.text[:160]}")

# 14) Adicional sin descripción / sin precio -> 400.
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"descripcion_libre": "   ", "precio_unitario": 500, "cantidad": 1, "porcentaje_ajuste": 0}])
check("Adicional sin descripción -> 400", r.status_code == 400, f"{r.status_code} {r.text[:160]}")
r = crear(h_sdl, ["servicios_lavanderia"], [
    {"descripcion_libre": "Flete", "cantidad": 1, "porcentaje_ajuste": 0}])
check("Adicional sin precio -> 400", r.status_code == 400, f"{r.status_code} {r.text[:160]}")

print()
sys.exit(1 if fallos else 0)
