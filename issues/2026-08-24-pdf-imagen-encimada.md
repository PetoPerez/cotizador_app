# La imagen del producto se encimaba sobre la cotización (PDF Supliese/Gamesail)

- **Fecha:** 2026-08-24
- **Estado:** Resuelto
- **Commit(s):** `b576835`
- **Reportado por / contexto:** captura de una cotización Supliese donde la imagen del equipo se superponía sobre la tabla del siguiente producto y sobre los totales.

## Síntoma / reporte
En el PDF, cuando un producto tenía imagen y **descripción corta**, la imagen se
salía de su bloque y se **encimaba** sobre la tabla del producto siguiente y sobre
el "PRESUPUESTO FINAL".

## Diagnóstico (causa raíz)
- La imagen flota a la derecha (`float`) dentro de `.char-wrap`, que usa
  `overflow:hidden` para contener el float.
- **WeasyPrint 68.1 NO contiene el float** cuando el bloque tiene poco/ningún texto
  en flujo (descripción corta) → el float se escapa hacia abajo y pisa lo demás.
- Las plantillas **clm/girbau nunca tuvieron el bug** porque limpian el float con
  un `<div style="clear:both">` explícito.

## Solución
Se agregó `<div style="clear:both"></div>` al final de `.char-wrap` (mismo patrón
que clm/girbau) en las **4 plantillas** con ese layout de imagen flotante:
`cotizacion_supliese.html`, `cotizacion_supliese_gamesail.html`,
`cotizacion_supliese_gomez.html` y la genérica `cotizacion.html`.

## Archivos tocados
- Las 4 plantillas mencionadas.

## Verificación
- **Reproducido** con WeasyPrint (imagen alta + descripción de 1 línea),
  renderizando a PDF y convirtiendo a PNG con `pdftoppm`:
  - Antes: imagen encimada sobre tabla y totales.
  - Después: imagen contenida en su propio renglón.
- Regresión `tests/test_pdf_totales.py` en verde.

## Prevención (que no reaparezca)
- **REGLA:** cualquier plantilla PDF con imagen flotante DEBE cerrar su contenedor
  con `<div style="clear:both">`. No confiar en `overflow:hidden` en WeasyPrint.
- Forma de verificar un bug visual de PDF: renderizar a PDF → PNG (`pdftoppm`) e
  inspeccionar la imagen.
