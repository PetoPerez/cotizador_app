# Descuentos editables para admin en cualquier empresa

- **Fecha:** 2026-08-17
- **Estado:** Resuelto
- **Commit(s):** `9b04fc2` (evolución de `e21730e`, `15f8cc7`, `59c80fe`)
- **Reportado por / contexto:** solicitud — habilitar descuentos editables al cotizar; los descuentos ya existían solo en SDL.

## Síntoma / reporte
El descuento (general + por ítem) solo existía en Servicios de Lavandería (SDL)
con tope 15%. Se pidió habilitarlo para **admin** en cualquier cotización.

## Diagnóstico (causa raíz)
- El gating del descuento estaba atado a `esModoServicios()` (SDL) en el frontend
  y a `empresa.codigo == 'servicios_lavanderia'` en el backend.
- **Punto crítico:** de las 6 plantillas PDF, **solo la de SDL** renderizaba el
  descuento. Habilitarlo en otras empresas sin tocar sus plantillas dejaría el
  descuento **invisible** en el PDF (subtotal y total no cuadrarían).

## Solución
- **Backend** (`cotizaciones.py`): gating por rol (`es_admin or SDL`) y tope por rol
  (100% admin / 15% vendedor) en el descuento por ítem y en el general.
- **Schema** (`schemas.py`): `descuento_pct` de `le=15` a `le=100` (el backend recorta según rol).
- **Frontend** (`cotizaciones.html`): `descuentoDisponible()` / `_capDescuento()` por
  rol; etiqueta/tope dinámicos (SDL = "póliza de mantenimiento preventivo";
  admin no-SDL = "Descuento general", sin tope).
- **PDF:** se agregó la línea `DESCUENTO (X%)` (entre Subtotal e IVA) + nota
  `Desc. %` por ítem a las **5 plantillas no-SDL** (clm, girbau, supliese,
  supliese_gamesail, supliese_gomez).

## Archivos tocados
- `app/routers/cotizaciones.py`, `app/schemas.py`, `app/templates/cotizaciones.html`
- 5 plantillas PDF no-SDL.

## Verificación
- Render real: reconciliación Subtotal − Descuento + IVA = Total.
- Retrocompatible: con descuento 0 las plantillas quedan idénticas.
- Regresión `tests/test_pdf_totales.py` en verde (6 empresas × 17 volúmenes).

## Prevención (que no reaparezca)
- Cualquier plantilla PDF nueva debe renderizar `cot.descuento_pct` y la nota por
  ítem si va a permitir descuentos, o el descuento quedará invisible.
- Nota de negocio: en SDL con admin y descuento >15%, el rótulo sigue diciendo
  "póliza de mantenimiento preventivo" (sigue siendo contexto SDL).
