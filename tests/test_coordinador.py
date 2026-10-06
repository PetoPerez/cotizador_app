"""Pruebas del rol coordinador de empresa.

El coordinador mantiene el catálogo de SU empresa (datos, imágenes, altas y
activar/desactivar ahí), pero no toca precios ni cotiza. Se prueban las piezas
puras que lo deciden, sin base de datos:

    venv/bin/python tests/test_coordinador.py
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

from app.routers.productos import _analizar_importacion, _exigir_su_empresa, _ProductoExistente
from app.security import require_catalogo, bloquear_coordinador

EMPRESAS = [
    SimpleNamespace(id="id-clm", codigo="clm", acronimo="CLM"),
    SimpleNamespace(id="id-gs", codigo="supliese_gamesail", acronimo="GS"),
]
GS = EMPRESAS[1]


def rechaza(fn, *args):
    try:
        fn(*args)
    except HTTPException as e:
        return e.status_code == 403
    return False


def usuario(rol, empresa_id="id-gs"):
    return SimpleNamespace(rol=rol, empresa_id=empresa_id)


# ── Permisos por rol ─────────────────────────────────────────────────────────
assert rechaza(bloquear_coordinador, usuario("coordinador"))       # no cotiza ni ve clientes
assert not rechaza(bloquear_coordinador, usuario("vendedor"))
assert not rechaza(require_catalogo, usuario("coordinador"))       # sí mantiene catálogo
assert rechaza(require_catalogo, usuario("vendedor"))

# Solo productos ligados a su empresa (aunque otras también los vendan).
compartido = SimpleNamespace(empresas=[SimpleNamespace(empresa_id="id-clm"),
                                       SimpleNamespace(empresa_id="id-gs")])
ajeno = SimpleNamespace(empresas=[SimpleNamespace(empresa_id="id-clm")])
assert not rechaza(_exigir_su_empresa, compartido, usuario("coordinador"))
assert rechaza(_exigir_su_empresa, ajeno, usuario("coordinador"))
assert not rechaza(_exigir_su_empresa, ajeno, usuario("admin", None))  # el admin toca todo

# ── Importación del coordinador: sin precios ─────────────────────────────────
catalogo = {
    # ya lo vende CLM, todavía no GS → se liga a GS
    ("girbau", "lavadora", "hs-6028"): _ProductoExistente(id="p1", descripcion="vieja",
                                                          precios={"clm": (100, True)}),
    # ya está en GS → no se vuelve a ligar
    ("girbau", "secadora", "sr-50"): _ProductoExistente(id="p2", descripcion="igual",
                                                        precios={"supliese_gamesail": (None, True)}),
}
rows = [
    ("marca", "equipo", "modelo", "descripcion", "precio_gs"),   # trae precio: se ignora
    ("GIRBAU", "Lavadora", "HS-6028", "", 999),                  # existente en otra empresa
    ("GIRBAU", "Secadora", "SR-50", "igual", ""),                 # ya en su empresa, sin cambios
    ("GIRBAU", "Planchadora", "PB-1", "nueva", ""),               # nueva, sin precio: no es error
]
r = _analizar_importacion(rows, EMPRESAS, catalogo, empresa_coord=GS)
assert r["error"] is None, r["error"]
assert not r["errores"], r["errores"]
assert any("precio_gs" in c for c in r["columnas_ignoradas"])
assert [x["modelo"] for x in r["nuevos"]] == ["PB-1"]
assert r["nuevos"][0]["precios"] == {}                           # entra sin precio
assert len(r["actualizar"]) == 1 and r["actualizar"][0]["ligar"]
assert r["actualizar"][0]["precios"] == {}                       # no cambia precios de nadie
assert r["sin_cambios"] == 1

# El admin sigue exigiendo precio (sin regresión).
r = _analizar_importacion([("marca", "equipo", "modelo"), ("X", "Y", "Z")], EMPRESAS, {})
assert r["error"] and "precio" in r["error"]

print("OK - test_coordinador")
