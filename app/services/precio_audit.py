"""Helpers de auditoría append-only.

`registrar_cambio_precio` y `registrar_cambio_estado` se usan desde los routers de
productos y servicios y desde scripts batch. Ninguno hace commit: agregan el
registro a la sesión y dejan que el llamador confirme la transacción junto con el
cambio, para que el historial y el cambio se guarden de forma atómica.
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


def ref_producto(producto, empresa=None) -> str:
    """Snapshot legible de un producto.

    Con `empresa`, agrega el acrónimo ("MARCA / EQUIPO / MODELO — CLM"); sin ella,
    devuelve solo la referencia base. El historial de estado no lleva el sufijo de
    empresa porque `activo` es del producto, no de un precio por empresa.
    """
    base = f"{producto.marca} / {producto.equipo} / {producto.modelo}"
    if empresa is None:
        return base
    acr = getattr(empresa, "acronimo", None) or getattr(empresa, "codigo", "?")
    return f"{base} — {acr}"


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


def debe_registrar_estado(activo_actual, activo_nuevo) -> bool:
    """True solo cuando el estado `activo` cambia de verdad.

    Evita llenar la bitácora de repeticiones: un `PUT` que reenvía el mismo valor
    (o que no trae `activo`) no deja registro. `activo_nuevo=None` significa "el
    payload no traía el campo"; se compara con `is None` para no confundir un
    `False` (desactivar) con la ausencia del campo.
    """
    if activo_nuevo is None:
        return False
    return bool(activo_actual) != bool(activo_nuevo)


def registrar_cambio_estado(
    db,
    *,
    producto,
    activo_nuevo,
    activo_anterior=None,
    usuario=None,           # objeto Usuario (o None para cambios de script)
    usuario_nombre=None,    # override del nombre (p. ej. "script")
    origen="manual",        # canal: manual | importacion | script
):
    """Agrega (sin commit) un registro al historial de estado de un producto.

    Devuelve el registro creado, o None si no hubo cambio real (activar uno ya
    activo, o desactivar uno ya inactivo).
    """
    if not debe_registrar_estado(activo_anterior, activo_nuevo):
        return None

    reg = models.ProductoEstadoHistorial(
        producto_id=getattr(producto, "id", None),
        referencia=ref_producto(producto),
        activo_nuevo=bool(activo_nuevo),
        usuario_id=getattr(usuario, "id", None),
        usuario_nombre=usuario_nombre or getattr(usuario, "nombre", None),
        origen=origen,
    )
    db.add(reg)
    return reg
