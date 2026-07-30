#!/usr/bin/env python3
"""Reorganiza el catálogo de servicios de Servicios de Lavandería.

Dos acciones, idempotentes:

1) Clasifica el `tipo` de cada servicio:
   - 'mantenimiento'    -> nombre con prefijo 'S-' (convención del catálogo).
   - 'puesta_en_marcha' -> descripción de configuración/ajuste inicial.
   - 'otro'             -> cargos sueltos sin descripción (flete, seguro...).

2) Desactiva los servicios MALFORMADOS: los que se importaron con las columnas
   corridas (nombre = tipo de equipo p.ej. "LAVADORA", descripción = un modelo
   p.ej. "TITAN SINGLE", sin descripción real). Se detectan porque su
   descripción es un texto corto (<=25) que parece modelo, no descripción.
   Casi todos son duplicados de un servicio de puesta en marcha bien cargado.

No borra nada: solo marca activo=False (reversible) y ajusta `tipo`.

Uso:
    python scripts/reorganizar_servicios.py           # dry-run (no escribe)
    python scripts/reorganizar_servicios.py --apply    # aplica

ATENCIÓN: usa el DATABASE_URL del .env (producción). Requiere que la columna
`servicios.tipo` ya exista (se crea en el on_startup al desplegar).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402

CARGOS = ("FLETE", "MANIOBRA", "SEGURO", "VIATICO", "TRASLADO")

# El catálogo se cargó con descripciones estándar; se reconocen por sus frases.
_FRASES_MANTTO = ("servicio de mantenimiento", "está diseñado", "esta disenado")
_FRASES_PUESTA = ("configuraci", "ajuste inicial")


def _tipo_reconocido(s):
    """Devuelve el tipo si la descripción/nombre coincide con un patrón limpio
    conocido; None si no se reconoce (registro malformado)."""
    nombre = (s.nombre or "")
    desc = (s.descripcion or "").strip()
    dl = desc.lower()
    if nombre.startswith("S-") or any(f in dl for f in _FRASES_MANTTO):
        return "mantenimiento"
    if any(f in dl for f in _FRASES_PUESTA):
        return "puesta_en_marcha"
    if not desc and any(k in nombre.upper() for k in CARGOS):
        return "otro"
    return None


def clasificar(s) -> str:
    """Tipo para la columna (los no reconocidos caen a 'mantenimiento' pero se
    desactivan)."""
    return _tipo_reconocido(s) or "mantenimiento"


def es_malformado(s) -> bool:
    """Malformado: la descripción no corresponde a ningún patrón limpio conocido
    (p.ej. descripción = un modelo, o 'MARCA X MODELO Y'), y no es un cargo."""
    return _tipo_reconocido(s) is None


def main():
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        servs = db.query(models.Servicio).all()
        tipos = {"mantenimiento": 0, "puesta_en_marcha": 0, "otro": 0}
        reclasificados = 0
        desactivados = 0
        ejemplos_desact = []

        for s in servs:
            nuevo_tipo = clasificar(s)
            tipos[nuevo_tipo] += 1
            if s.tipo != nuevo_tipo:
                reclasificados += 1
                if apply:
                    s.tipo = nuevo_tipo

            if es_malformado(s) and s.activo:
                desactivados += 1
                if len(ejemplos_desact) < 10:
                    ejemplos_desact.append(f"  {s.nombre!r}  (desc={s.descripcion!r})")
                if apply:
                    s.activo = False

        if apply:
            db.commit()

        print("=" * 64)
        print("REORGANIZAR SERVICIOS" + ("  (APLICADO)" if apply else "  (DRY-RUN)"))
        print("=" * 64)
        print(f"  Total servicios              : {len(servs)}")
        print(f"  Clasificación de tipo:")
        print(f"     mantenimiento             : {tipos['mantenimiento']}")
        print(f"     puesta_en_marcha          : {tipos['puesta_en_marcha']}")
        print(f"     otro                      : {tipos['otro']}")
        print(f"  Servicios a reclasificar     : {reclasificados}")
        print(f"  Servicios malformados a desactivar: {desactivados}")
        if ejemplos_desact:
            print("\n  Ejemplos de malformados desactivados:")
            print("\n".join(ejemplos_desact))
        print("\n" + ("✓ Cambios aplicados." if apply else "Dry-run. Para aplicar, corre con  --apply"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
