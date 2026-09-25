"""Quién puede ver los productos desactivados en el catálogo.

Blinda el caso GXS-17: un producto desactivado desaparecía de la pantalla de
Productos para siempre, así que desactivar equivalía a borrar. Ahora el admin
puede pedirlos con ?incluir_inactivos=true; el vendedor nunca los ve, porque un
producto desactivado no debe poder cotizarse.

    venv/bin/python tests/test_productos_inactivos.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.productos import _puede_ver_inactivos

# El admin los ve solo cuando los pide.
assert _puede_ver_inactivos(True, "admin")
assert _puede_ver_inactivos(True, "superadmin")
assert not _puede_ver_inactivos(False, "admin")
assert not _puede_ver_inactivos(False, "superadmin")

# El vendedor no los ve ni pidiéndolos: no debe poder cotizar un desactivado.
assert not _puede_ver_inactivos(True, "vendedor")
assert not _puede_ver_inactivos(False, "vendedor")

print("OK - test_productos_inactivos")
