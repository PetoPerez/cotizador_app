#!/usr/bin/env python3
"""Backfill de "línea base" del historial de precios.

La auditoría (`precio_historial`) es prospectiva: solo registra cambios a partir
de que se activó. Los precios que ya existían y no se han tocado no aparecen en
el historial. Este script inserta una fila de línea base por cada precio vigente
—producto por empresa y servicio— que aún NO tenga ningún registro, para que el
reporte de auditoría esté completo desde un punto de partida.

Es idempotente: si un precio ya tiene historial (línea base o un cambio real) se
omite, así que correrlo de nuevo no duplica.

Uso:
    python scripts/backfill_historial_precios.py            # dry-run (no escribe)
    python scripts/backfill_historial_precios.py --apply    # aplica

ATENCIÓN: usa el DATABASE_URL del .env (base de producción).
"""
import os
import sys

# Permite importar el paquete `app` al correr desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.services.precio_audit import ref_producto  # noqa: E402

ORIGEN = "linea_base"
AUTOR = "línea base"


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        creados_prod = 0
        creados_svc = 0
        omitidos_prod = 0
        omitidos_svc = 0
        ejemplos = []

        # ── Precios de producto por empresa ──
        pes = (db.query(models.ProductoEmpresa)
                 .join(models.Producto, models.Producto.id == models.ProductoEmpresa.producto_id)
                 .join(models.Empresa, models.Empresa.id == models.ProductoEmpresa.empresa_id)
                 .all())
        for pe in pes:
            ya = (db.query(models.PrecioHistorial.id)
                    .filter(models.PrecioHistorial.producto_id == pe.producto_id,
                            models.PrecioHistorial.empresa_id == pe.empresa_id)
                    .first())
            if ya:
                omitidos_prod += 1
                continue
            ref = ref_producto(pe.producto, pe.empresa)
            if apply:
                db.add(models.PrecioHistorial(
                    tipo="producto",
                    producto_id=pe.producto_id,
                    empresa_id=pe.empresa_id,
                    referencia=ref,
                    precio_anterior=None,      # es la línea base (un alta)
                    precio_nuevo=pe.precio_lista,
                    usuario_id=None,
                    usuario_nombre=AUTOR,
                    origen=ORIGEN,
                ))
            creados_prod += 1
            if len(ejemplos) < 8:
                ejemplos.append(f"  {ref} = {pe.precio_lista}")

        # ── Precios de servicios ──
        for s in db.query(models.Servicio).all():
            ya = (db.query(models.PrecioHistorial.id)
                    .filter(models.PrecioHistorial.servicio_id == s.id)
                    .first())
            if ya:
                omitidos_svc += 1
                continue
            if apply:
                db.add(models.PrecioHistorial(
                    tipo="servicio",
                    servicio_id=s.id,
                    referencia=s.nombre,
                    precio_anterior=None,
                    precio_nuevo=s.precio_unitario,
                    usuario_id=None,
                    usuario_nombre=AUTOR,
                    origen=ORIGEN,
                ))
            creados_svc += 1

        if apply:
            db.commit()

        print("=" * 60)
        print("BACKFILL LÍNEA BASE" + ("  (APLICADO)" if apply else "  (DRY-RUN)"))
        print("=" * 60)
        print(f"  Líneas base de producto-empresa a crear: {creados_prod}")
        print(f"  Líneas base de servicio a crear        : {creados_svc}")
        print(f"  Producto-empresa ya con historial      : {omitidos_prod}")
        print(f"  Servicios ya con historial             : {omitidos_svc}")
        if ejemplos:
            print("\n  Ejemplos:")
            print("\n".join(ejemplos))
        if not apply:
            print("\nDry-run. Para aplicar, corre de nuevo con  --apply")
        else:
            print(f"\n✓ Aplicado: {creados_prod + creados_svc} línea(s) base insertada(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
