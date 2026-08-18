"""Pruebas de la importación de productos por Excel.

Blindan el comportamiento reportado como falla: "como si no dejara cargar datos
nuevos ni actualizar los existentes". Cubren los tres síntomas posibles:

  A) NO CARGA nuevos          -> encabezados/precios mal interpretados.
  B) NO ACTUALIZA existentes  -> el match no reconoce el producto (mayúsculas/espacios)
                                 y lo trata como nuevo (duplicado), o lo da por igual.
  C) RECHAZA el archivo        -> extensión en mayúsculas, archivo vacío, sin columnas.

Se prueban las funciones PURAS extraídas del endpoint (sin base de datos ni red),
así corren en cualquier entorno —incluido CI— sin Docker ni Postgres:

    venv/bin/python tests/test_import_productos.py

`_analizar_importacion(rows, empresas, catalogo)` es exactamente la lógica que usa
POST /productos/importar para clasificar el Excel; el endpoint solo arma el catálogo
desde la BD y aplica el resultado. Por eso cubrir esta función cubre el bug.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.productos import (
    _analizar_importacion, _norm_clave, _extension_valida,
    _parsear_precio_import, _ProductoExistente,
)

# ── Empresas importables de prueba (como _empresas_para_import, sin SDL) ──────
EMPRESAS = [
    SimpleNamespace(id="id-clm", codigo="clm", acronimo="CLM"),
    SimpleNamespace(id="id-gs",  codigo="supliese_gamesail", acronimo="GS"),
    SimpleNamespace(id="id-sup", codigo="supliese", acronimo="SUP"),
    SimpleNamespace(id="id-gir", codigo="girbau", acronimo="GIR"),
]
HEADER = ["marca", "equipo", "modelo", "descripcion",
          "precio_general", "precio_clm", "precio_gs", "precio_sup", "precio_gir"]


def rows(*filas):
    """Construye la matriz de filas (encabezado + datos) que entrega openpyxl."""
    return [tuple(HEADER)] + [tuple(f) for f in filas]


def fila(marca="", equipo="", modelo="", desc="",
         general="", clm="", gs="", sup="", gir=""):
    return [marca, equipo, modelo, desc, general, clm, gs, sup, gir]


def existente(pid, desc=None, **precios):
    """precios: codigo -> precio (activo=True) o codigo -> (precio, activo)."""
    p = {}
    for cod, val in precios.items():
        p[cod] = val if isinstance(val, tuple) else (val, True)
    return _ProductoExistente(id=pid, descripcion=desc, precios=p)


fallos = []


def check(nombre, cond, detalle=""):
    print(("✅ " if cond else "❌ ") + nombre + ("" if cond else f"  -> {detalle}"))
    if not cond:
        fallos.append(nombre)


# ════════════════════════════════════════════════════════════════════════════
# ESCENARIO C — el archivo se rechaza / no se puede leer
# ════════════════════════════════════════════════════════════════════════════
print("\n── C) Rechazo / validación de formato ──")

check("extensión .xlsx válida", _extension_valida("lista.xlsx"))
check("extensión .xls válida", _extension_valida("lista.xls"))
# F1: antes un nombre en MAYÚSCULAS se rechazaba ("no me deja cargar").
check("extensión .XLSX en MAYÚSCULAS válida (F1)", _extension_valida("LISTA.XLSX"))
check("extensión .Xlsx mixta válida (F1)", _extension_valida("Lista_Precios.Xlsx"))
check("extensión con espacios al final válida", _extension_valida("lista.xlsx  "))
check("archivo .pdf rechazado", not _extension_valida("lista.pdf"))
check("nombre vacío rechazado", not _extension_valida(""))
check("nombre None rechazado", not _extension_valida(None))

r = _analizar_importacion([], EMPRESAS, {})
check("archivo vacío -> error claro", r["error"] == "El archivo está vacío", r["error"])

# Encabezados sin 'modelo'
r = _analizar_importacion([("marca", "equipo", "precio_clm"), ("GIRBAU", "Lavadora", 100)],
                          EMPRESAS, {})
check("falta columna 'modelo' -> error de formato", r["error"] and "modelo" in r["error"], r["error"])

# Sin ninguna columna de precio reconocida
r = _analizar_importacion([("marca", "equipo", "modelo", "precio"),
                           ("GIRBAU", "Lavadora", "HS-6028", 100)], EMPRESAS, {})
check("sin columna de precio reconocida -> error de formato",
      r["error"] and "precio" in r["error"], r["error"])


# ════════════════════════════════════════════════════════════════════════════
# ESCENARIO A — cargar productos NUEVOS
# ════════════════════════════════════════════════════════════════════════════
print("\n── A) Alta de productos nuevos ──")

r = _analizar_importacion(rows(
    fila(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028", desc="28kg", gir=75000),
    fila(marca="MAYTAG", equipo="Secadora", modelo="MDG-30", clm=42000),
), EMPRESAS, {})
check("2 filas válidas -> 2 nuevos", r["error"] is None and len(r["nuevos"]) == 2,
      f'{r["error"]} nuevos={len(r["nuevos"])}')
check("nuevo toma el precio de su empresa (GIR=75000)",
      r["nuevos"] and r["nuevos"][0]["precios"].get("girbau") == 75000,
      str(r["nuevos"][0]["precios"]) if r["nuevos"] else "-")
check("sin actualizaciones ni errores", not r["actualizar"] and not r["errores"])

# precio_general se reparte a TODAS las empresas
r = _analizar_importacion(rows(
    fila(marca="ACME", equipo="Prensa", modelo="P-1", general=1000),
), EMPRESAS, {})
precios = r["nuevos"][0]["precios"] if r["nuevos"] else {}
check("precio_general se aplica a las 4 empresas",
      all(precios.get(e.codigo) == 1000 for e in EMPRESAS), str(precios))

# Precio como texto con $ y separador de miles
r = _analizar_importacion(rows(
    fila(marca="ACME", equipo="Prensa", modelo="P-2", clm="$1,234.50"),
), EMPRESAS, {})
check("precio '$1,234.50' se interpreta como 1234.5",
      r["nuevos"] and r["nuevos"][0]["precios"].get("clm") == 1234.5,
      str(r["nuevos"][0]["precios"]) if r["nuevos"] else "-")

# Fila sin marca -> 'General' y se cuenta en sin_marca
r = _analizar_importacion(rows(
    fila(equipo="Bomba", modelo="B-9", clm=500),
), EMPRESAS, {})
check("fila sin marca -> marca 'General' y sin_marca=1",
      r["nuevos"] and r["nuevos"][0]["marca"] == "General" and r["sin_marca"] == 1,
      f'marca={r["nuevos"][0]["marca"] if r["nuevos"] else "-"} sin_marca={r["sin_marca"]}')


# ════════════════════════════════════════════════════════════════════════════
# ESCENARIO B — ACTUALIZAR productos existentes (el corazón del bug)
# ════════════════════════════════════════════════════════════════════════════
print("\n── B) Actualización de existentes ──")

# Catálogo: un GIRBAU/Lavadora/HS-6028 con precio GIR=70000
cat = {
    (_norm_clave("GIRBAU"), _norm_clave("Lavadora"), _norm_clave("HS-6028")):
        existente("p1", desc="28kg", girbau=70000),
}

# Precio cambia -> va a 'actualizar', no a 'nuevos'
r = _analizar_importacion(rows(
    fila(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028", gir=75000),
), EMPRESAS, cat)
check("precio cambiado -> 1 actualizar, 0 nuevos",
      len(r["actualizar"]) == 1 and len(r["nuevos"]) == 0,
      f'act={len(r["actualizar"])} nuevos={len(r["nuevos"])}')
check("el cambio describe 70,000 -> 75,000",
      r["actualizar"] and any("70,000.00 → 75,000.00" in c for c in r["actualizar"][0]["cambios"]),
      str(r["actualizar"][0]["cambios"]) if r["actualizar"] else "-")

# Mismo precio -> sin_cambios (F4: comportamiento correcto, no es bug)
r = _analizar_importacion(rows(
    fila(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028", gir=70000),
), EMPRESAS, cat)
check("precio idéntico -> sin_cambios=1, sin actualizar/nuevos",
      r["sin_cambios"] == 1 and not r["actualizar"] and not r["nuevos"],
      f'sc={r["sin_cambios"]} act={len(r["actualizar"])} nuevos={len(r["nuevos"])}')

# ── F2: el Excel trae otra CAJA (mayúsculas) -> debe ACTUALIZAR, no duplicar ──
r = _analizar_importacion(rows(
    fila(marca="girbau", equipo="LAVADORA", modelo="hs-6028", gir=80000),
), EMPRESAS, cat)
check("match INSENSIBLE a mayúsculas -> actualiza (no duplica) (F2)",
      len(r["actualizar"]) == 1 and len(r["nuevos"]) == 0,
      f'act={len(r["actualizar"])} nuevos={len(r["nuevos"])}')

# ── F2: espacios extra / dobles espacios -> mismo producto ──
r = _analizar_importacion(rows(
    fila(marca="  GIRBAU ", equipo="Lavadora", modelo="HS-6028", gir=80000),
), EMPRESAS, cat)
check("match tolerante a espacios -> actualiza (no duplica) (F2)",
      len(r["actualizar"]) == 1 and len(r["nuevos"]) == 0,
      f'act={len(r["actualizar"])} nuevos={len(r["nuevos"])}')

# Precio nuevo para una empresa que el producto aún no tenía -> es un cambio (alta de precio)
r = _analizar_importacion(rows(
    fila(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028", clm=99000),
), EMPRESAS, cat)
check("precio en empresa nueva (CLM) del producto existente -> actualizar",
      len(r["actualizar"]) == 1 and any("CLM" in c for c in r["actualizar"][0]["cambios"]),
      str(r["actualizar"][0]["cambios"]) if r["actualizar"] else "-")

# Producto existente pero con precio INACTIVO -> reactivar cuenta como cambio
cat_inact = {
    (_norm_clave("ACME"), _norm_clave("Bomba"), _norm_clave("B-1")):
        existente("p2", clm=(500, False)),  # precio existe pero inactivo
}
r = _analizar_importacion(rows(
    fila(marca="ACME", equipo="Bomba", modelo="B-1", clm=500),
), EMPRESAS, cat_inact)
check("precio inactivo con mismo valor -> se reactiva (actualizar)",
      len(r["actualizar"]) == 1, f'act={len(r["actualizar"])} sc={r["sin_cambios"]}')

# Cambia solo la descripción
r = _analizar_importacion(rows(
    fila(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028", desc="28kg inverter", gir=70000),
), EMPRESAS, cat)
check("cambia solo la descripción -> actualizar con 'descripción'",
      len(r["actualizar"]) == 1 and "descripción" in r["actualizar"][0]["cambios"],
      str(r["actualizar"][0]["cambios"]) if r["actualizar"] else "-")


# ════════════════════════════════════════════════════════════════════════════
# Filas problemáticas: se reportan como error SIN abortar el resto
# ════════════════════════════════════════════════════════════════════════════
print("\n── Errores por fila (no deben tumbar la carga completa) ──")

r = _analizar_importacion(rows(
    fila(marca="OK", equipo="Equipo", modelo="M1", clm=100),   # válida
    fila(marca="X", equipo="Equipo"),                          # falta modelo
    fila(marca="Y", equipo="Equipo", modelo="M3"),             # sin precio
    fila(),                                                     # en blanco -> se ignora
), EMPRESAS, {})
check("1 nueva válida pese a filas con error", len(r["nuevos"]) == 1, f'nuevos={len(r["nuevos"])}')
check("2 filas reportadas como error", len(r["errores"]) == 2, str(r["errores"]))
check("fila en blanco se ignora (no cuenta como error)",
      len(r["errores"]) == 2 and r["sin_cambios"] == 0)


# ── _parsear_precio_import: casos límite ──
print("\n── Parseo de precios ──")
casos = [
    ("100", 100.0), (100, 100.0), (1234.5, 1234.5),
    ("$1,234.50", 1234.5), ("  2,000  ", 2000.0),
    ("", None), (None, None), ("0", None), ("-5", None), ("abc", None),
]
for raw, esperado in casos:
    got = _parsear_precio_import(raw)
    check(f"parsear {raw!r} -> {esperado}", got == esperado, f"got={got}")


# ════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
if fallos:
    print(f"❌ {len(fallos)} prueba(s) fallaron:")
    for f in fallos:
        print("   -", f)
    sys.exit(1)
print("✅ Todas las pruebas de importación pasaron.")
