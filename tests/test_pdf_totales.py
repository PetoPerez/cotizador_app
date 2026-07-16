#!/usr/bin/env python3
"""Regresión: el total de la cotización nunca debe quedar tapado por el footer.

Contexto del bug (cotización 260716-SUP-13-010): en las plantillas de la familia
`supliese` el footer fijo usaba `bottom: 0`, que ancla al fondo del área de
CONTENIDO (no al borde de la página). Como el footer es opaco (background:#fff,
z-index:100) pintaba encima de las últimas filas y el `Total:` desaparecía.

El test renderiza cada plantilla de empresa barriendo el volumen de contenido,
de modo que el bloque de totales aterrice en muchas posiciones verticales —
incluida la franja peligrosa junto al footer— y comprueba dos invariantes:

  1. El footer no invade el área de contenido (invariante estructural).
  2. La caja que contiene el importe total no se solapa con el footer.

Uso:
    python tests/test_pdf_totales.py           # todas las empresas
    python tests/test_pdf_totales.py supliese  # filtra por plantilla
"""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.services.pdf_service import _fecha_es
from app.utils.numero_letras import numero_a_letras

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(BASE, "app", "templates")
STATIC_URL = "file://" + os.path.join(BASE, "app", "static") + "/"
env = Environment(loader=FileSystemLoader(TPL_DIR))

PX_PER_MM = 96 / 25.4

# (código de empresa, plantilla) — refleja el mapeo de app/main.py y pdf_service.py
EMPRESAS = [
    ("clm",                  "cotizacion_clm.html"),
    ("supliese_gamesail",    "cotizacion_supliese_gamesail.html"),
    ("supliese",             "cotizacion_supliese.html"),
    ("servicios_lavanderia", "cotizacion_servicios_lavanderia.html"),
    ("girbau",               "cotizacion_girbau.html"),
    ("supliese_gomez",       "cotizacion_supliese_gomez.html"),  # alias legacy
]

# Importe distintivo: no colisiona con subtotal ni IVA al buscarlo en el texto.
TOTAL = 438852.38
TOTAL_TXT = "438,852.38"
SUBTOTAL = 378321.02
IVA = 60531.36


class Obj:
    """Namespace simple (no hereda de dict: `cot.items` chocaría con dict.items)."""
    def __init__(self, **kw):
        self.__dict__.update(kw)
    def __getattr__(self, _):
        return None


def _item(clave, precio, bullets):
    desc = "GAMESAIL Equipo industrial.\n" + "\n".join(
        f"* Característica de prueba número {i} del equipo." for i in range(bullets))
    return Obj(
        cantidad=1, precio_final=precio, importe=precio,
        producto=Obj(modelo=clave, marca="GAMESAIL", equipo="Equipo industrial",
                     descripcion=desc, imagen_url=None, imagenes=[]),
        servicio=Obj(nombre=clave, descripcion=desc, precio_unitario=precio),
        descripcion_libre=None,
    )


def _contexto(empresa_codigo, bullets):
    cot = Obj(
        numero_cotizacion="260716-SUP-13-010",
        subtotal=SUBTOTAL, iva=IVA, total=TOTAL,
        moneda="MXN", tipo_cambio=1, fecha=datetime(2026, 7, 16),
        items=[_item("XGQ-20FII / 20KG.", 251517.42, bullets),
               _item("GQZ-30 / 30 KG", 126803.60, max(0, bullets - 6))],
        notas=None,
        cliente=Obj(nombre_razon_social="LUIS ARTURO RODRIGUEZ", telefono="4433665258",
                    email="icasamich@gmail.com", atencion_nombre="LUIS ARTURO RODRIGUEZ",
                    atencion_titulo="", ciudad="Guadalajara", estado="Jalisco", pais="México"),
        vendedor=Obj(nombre="Silvia Molina Supliese", telefono="3311859797"),
        alcance_servicio="Alcance de prueba", tiempo_entrega="4 semanas",
        forma_pago="50% anticipo", ciudad_entrega="Guadalajara",
    )
    empresa = Obj(
        nombre="Empresa de prueba", marca="SUP", nombre_corto="Prueba",
        direccion="Calle la Luna 2921 Col. Jardines del Bosque Norte, Guadalajara, Jalisco",
        telefono="33 2300 1300", email="ventas@ejemplo.com", rfc="SGO210826M44",
        logo_url="images/supliese.jpeg", logo_decoracion_url="images/supliese_r.jpeg",
        acronimo="SUP", codigo=empresa_codigo,
    )
    return dict(cot=cot, empresa=empresa, fecha_es=_fecha_es, moneda="MXN", tc=1,
                float=float, numero_a_letras=numero_a_letras)


def _walk(box):
    yield box
    for child in getattr(box, "all_children", lambda: [])():
        yield from _walk(child)


def _classes(box):
    el = getattr(box, "element", None)
    if el is None or not hasattr(el, "get"):
        return ""
    return el.get("class") or ""


def _text(box):
    if hasattr(box, "text"):
        return box.text or ""
    return "".join(_text(c) for c in getattr(box, "all_children", lambda: [])())


def _margin_bottom_px(tpl):
    src = open(os.path.join(TPL_DIR, tpl)).read()
    decl = re.search(r"@page\s*\{[^}]*?margin:\s*([^;]+);", src, re.S).group(1).strip()
    parts = decl.split()
    raw = parts[2] if len(parts) == 4 else parts[-1]
    if raw.endswith("mm"):
        return float(raw[:-2]) * PX_PER_MM
    return float(re.sub(r"[^\d.]", "", raw) or 0)


def _footer_box(page):
    """Caja del footer fijo más externo de la página (la de borde superior más alto)."""
    cajas = [b for b in _walk(page._page_box) if "footer" in _classes(b)]
    return min(cajas, key=lambda b: b.position_y) if cajas else None


def _footer_top(page):
    """Borde superior del footer fijo más externo de la página."""
    box = _footer_box(page)
    return box.position_y if box is not None else None


def _footer_bottom(box):
    """Borde inferior de la caja de borde del footer (incluye padding y borde)."""
    return (box.position_y + box.height
            + getattr(box, "padding_top", 0) + getattr(box, "padding_bottom", 0)
            + getattr(box, "border_top_width", 0) + getattr(box, "border_bottom_width", 0))


def _total_box(pages):
    """Devuelve (pagina, caja) de la línea que contiene el importe total."""
    for page in pages:
        for box in _walk(page._page_box):
            if not hasattr(box, "text"):
                continue
            if TOTAL_TXT in (box.text or ""):
                return page, box
    return None, None


def revisar(empresa_codigo, tpl, bullets):
    """Devuelve lista de fallos (vacía si todo bien)."""
    html = env.get_template(tpl).render(**_contexto(empresa_codigo, bullets))
    pages = HTML(string=html, base_url=STATIC_URL).render().pages
    fallos = []

    # Invariante 1: el footer no invade el área de contenido de ninguna página.
    # Invariante 3: el footer tampoco se sale por debajo del borde de la hoja
    # (riesgo del propio fix: el `bottom` negativo lo empuja hacia el margen).
    margin_bottom = _margin_bottom_px(tpl)
    for i, page in enumerate(pages, 1):
        fbox = _footer_box(page)
        if fbox is None:
            continue
        invasion = (page.height - margin_bottom) - fbox.position_y
        if invasion > 0.5:
            fallos.append(f"pág {i}: el footer invade {invasion:.1f}px del área de contenido")
        desborde = _footer_bottom(fbox) - page.height
        if desborde > 0.5:
            fallos.append(f"pág {i}: el footer se sale {desborde:.1f}px por debajo de la hoja")

    # Invariante 2: el importe total no queda solapado por el footer.
    page, box = _total_box(pages)
    if box is None:
        fallos.append(f"el importe total {TOTAL_TXT} no aparece en el PDF")
    else:
        ftop = _footer_top(page)
        if ftop is not None:
            bottom = box.position_y + box.height
            if bottom > ftop:
                fallos.append(f"el footer tapa el total por {bottom - ftop:.1f}px")
    return fallos


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    objetivos = [(c, t) for c, t in EMPRESAS if filtro in c or filtro in t]
    if not objetivos:
        print(f"Ninguna empresa coincide con '{filtro}'")
        return 1

    # Barrido: mueve el bloque de totales por toda la página, incluida la franja
    # peligrosa junto al footer (que es donde se manifestó el bug).
    volumenes = list(range(0, 34, 2))
    total_fallos = 0

    for codigo, tpl in objetivos:
        errores = []
        for bullets in volumenes:
            for f in revisar(codigo, tpl, bullets):
                errores.append(f"  bullets={bullets:>2}: {f}")
        if errores:
            total_fallos += len(errores)
            print(f"❌ {codigo:22s} ({tpl})")
            for e in errores[:6]:
                print(e)
            if len(errores) > 6:
                print(f"  ... y {len(errores) - 6} caso(s) más")
        else:
            print(f"✅ {codigo:22s} total visible en {len(volumenes)} volúmenes de contenido")

    print()
    if total_fallos:
        print(f"FALLÓ: {total_fallos} caso(s) con el total tapado o footer invasivo")
        return 1
    print(f"OK: {len(objetivos)} empresa(s) × {len(volumenes)} volúmenes — el total siempre visible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
