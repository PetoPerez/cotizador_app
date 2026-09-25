# Carga por Excel no cargaba productos nuevos ni actualizaba los existentes

- **Fecha:** 2026-08-17
- **Estado:** Resuelto
- **Commit(s):** `2dbe69f`
- **Reportado por / contexto:** reporte de uso — "como si no dejara cargar datos nuevos ni actualizar los existentes" al importar productos por Excel.

## Síntoma / reporte
Al subir el Excel de productos, no se cargaban altas ni se aplicaban cambios; en
algunos casos el archivo se rechazaba.

## Diagnóstico (causa raíz)
Dos defectos en `app/routers/productos.py`:
- **F1 — extensión sensible a mayúsculas:** `file.filename.endswith((".xlsx",".xls"))`
  rechazaba archivos como `LISTA.XLSX` (mayúsculas).
- **F2 — emparejamiento exacto y sensible a mayúsculas/espacios:** el match con el
  producto existente comparaba `marca/equipo/modelo` de forma exacta, así que
  `"Girbau"` vs `"GIRBAU"` (o espacios distintos) creaba un **duplicado** en vez de
  actualizar.

## Solución
- `_extension_valida()` acepta la extensión sin importar mayúsculas.
- Emparejamiento por **clave normalizada** `_norm_clave` (minúsculas + espacios
  colapsados); el índice del catálogo se arma en **una sola consulta**.
- Se extrajo la clasificación de filas a una **función pura sin base de datos**
  (`_analizar_importacion`) para poder probarla en aislamiento. El contrato de la
  API (vista previa → confirmar) no cambió.

## Archivos tocados
- `app/routers/productos.py`
- `tests/test_import_productos.py` (nuevo — 39 aserciones)

## Verificación
- `venv/bin/python tests/test_import_productos.py` → 39 aserciones en verde
  (corre sin Docker/Postgres/pytest): altas, actualización case-insensitive,
  rechazos de formato, parseo de precios.

## Prevención (que no reaparezca)
- La suite `tests/test_import_productos.py` blinda alta/actualización/rechazos.
- Pendiente (cuando haya Postgres local): E2E real del endpoint `/productos/importar`.
- Ojo: F2 al normalizar podría fusionar dos productos ya existentes que difieran
  solo por caja (dato sucio previo).
