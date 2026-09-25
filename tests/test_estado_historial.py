"""Cuándo se registra un cambio de `activo` en la bitácora de estado.

Blinda el caso GXS-17: un producto cotizado "desapareció" del catálogo y nadie
sabía quién lo desactivó, porque `productos.activo` no dejaba rastro. Ahora cada
activación/desactivación se registra en `producto_estado_historial`, pero SOLO
cuando el valor cambia de verdad: un `PUT` que reenvía el mismo `activo` (o que no
lo trae) no debe dejar renglones repetidos.

Se prueba la función PURA extraída del registro, sin base de datos ni red, así
corre en cualquier entorno (incluido CI) sin Docker ni Postgres:

    venv/bin/python tests/test_estado_historial.py
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.precio_audit import (
    debe_registrar_estado, ref_producto,
)

# ── Cambios reales: desactivar (True -> False) y activar (False -> True) ──
assert debe_registrar_estado(True, False)
assert debe_registrar_estado(False, True)

# ── El PUT reenvía el mismo valor: no se registra ──
assert not debe_registrar_estado(True, True)
assert not debe_registrar_estado(False, False)

# ── El payload no trae `activo` (PUT parcial): no se registra ──
assert not debe_registrar_estado(True, None)
assert not debe_registrar_estado(False, None)

# ── La referencia es el snapshot del producto, sin el sufijo de empresa ──
p = SimpleNamespace(marca="GIRBAU", equipo="Lavadora", modelo="HS-6028")
assert ref_producto(p) == "GIRBAU / Lavadora / HS-6028", ref_producto(p)
emp = SimpleNamespace(acronimo="CLM")
assert ref_producto(p, emp) == "GIRBAU / Lavadora / HS-6028 — CLM", ref_producto(p, emp)

print("OK - test_estado_historial")
