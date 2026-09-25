# Ajuste de precio: slider ±5% para vendedores, porcentaje libre para admin

- **Fecha:** 2026-08-17 → 2026-08-19
- **Estado:** Resuelto
- **Commit(s):** `8dda469` (quitar slider), `8eccc39` (restaurar con reglas por rol)
- **Reportado por / contexto:** el control de "Ajuste de precio" se confundía con el descuento.

## Síntoma / reporte
1. La barra (slider) que se arrastraba se confundía con "aplicar un descuento",
   pero en realidad ajustaba el precio dentro del margen del vendedor. Creaba
   confusión → se pidió quitarla (`8dda469`).
2. Después se pidió **regresar el slider** con reglas nuevas: visible para todos
   con capacidad de **±5%**, y **solo admin** con porcentaje **libre** (`8eccc39`).

## Diagnóstico (causa raíz)
- El "Ajuste de precio" (`porcentaje_ajuste`) es un mecanismo **distinto** del
  descuento: mueve el precio de lista dentro de un rango (puede subir o bajar) y
  **NO se rotula** en el PDF (aparece como precio de lista).
- Antes el rango era el margen por usuario (`margen_min`/`margen_max`), lo que se
  prestaba a confusión con el descuento recién agregado.

## Solución (estado final)
- **Vendedores/servicios:** slider fijo **±5%** (ya NO usa el margen por usuario).
- **Admin/superadmin:** campo numérico de **% libre** (sin tope), no slider.
- **Frontend** (`cotizaciones.html`): `ajusteControlHTML()` elige slider o input
  numérico según `isAdmin`; helpers `_ajusteMin/_ajusteMax`; el control
  (`id="ajuste-ctrl-i"`) se sincroniza con el campo "Unitario $".
- **Backend** (`cotizaciones.py`): valida ±5% para no-admin, libre para admin.

## Archivos tocados
- `app/routers/cotizaciones.py`, `app/templates/cotizaciones.html`

## Verificación
- `node --check` del JS + `ast.parse` del Python.
- Simulación del clamp: vendedor limitado a ±5 (borde rojo si se sale vía
  "Unitario $"); admin acepta cualquier % (30, −40…).

## Prevención (que no reaparezca)
- **NO confundir** los dos mecanismos:
  - **Ajuste de precio** → mueve el precio dentro de rango, puede subir o bajar,
    **no se rotula** en PDF (se ve como precio de lista).
  - **Descuento** (campos Desc% / general) → **sí se rotula** en el PDF.
- Si en el futuro se quieren márgenes por vendedor, revertir el ±5% fijo.
