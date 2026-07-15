"""Helper para registrar cambios de precio en la tabla `precio_historial`.

Se usa desde los routers de productos y servicios y desde el script batch de
actualización de precios. No hace commit: agrega el registro a la sesión y deja
que el llamador confirme la transacción junto con el cambio de precio, para que
el historial y el precio se guarden de forma atómica.
"""
from decimal import Decimal, InvalidOperation

from app import models


def _to_dec(v):
    if v is None:
        return None
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def ref_producto(producto, empresa) -> str:
    """Snapshot legible de un precio de producto por empresa."""
    acr = getattr(empresa, "acronimo", None) or getattr(empresa, "codigo", "?")
    return f"{producto.marca} / {producto.equipo} / {producto.modelo} — {acr}"


def registrar_cambio_precio(
    db,
    *,
    tipo,                    # 'producto' | 'servicio'
    referencia,             # snapshot legible
    precio_nuevo,
    precio_anterior=None,   # None en un alta
    producto_id=None,
    empresa_id=None,
    servicio_id=None,
    usuario=None,           # objeto Usuario (o None para cambios de script)
    usuario_nombre=None,    # override del nombre (p. ej. "script")
    origen="manual",        # canal: manual | importacion | script (alta = precio_anterior None)
):
    """Agrega (sin commit) un registro al historial de precios.

    Devuelve el registro creado, o None si no hubo cambio real (precio anterior
    igual al nuevo), para no ensuciar el historial con no-cambios.
    """
    ant = _to_dec(precio_anterior)
    nue = _to_dec(precio_nuevo)
    if nue is None:
        return None
    if ant is not None and ant == nue:
        return None  # sin cambio real

    reg = models.PrecioHistorial(
        tipo=tipo,
        referencia=referencia,
        precio_anterior=ant,
        precio_nuevo=nue,
        producto_id=producto_id,
        empresa_id=empresa_id,
        servicio_id=servicio_id,
        usuario_id=getattr(usuario, "id", None),
        usuario_nombre=usuario_nombre or getattr(usuario, "nombre", None),
        origen=origen,
    )
    db.add(reg)
    return reg
