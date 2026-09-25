# El despliegue en Railway se cayó por dependencias sin versión fija

- **Fecha:** 2026-09-24
- **Estado:** Resuelto
- **Commit(s):** pendiente de asignar (fija versiones en `requirements.txt`)
- **Reportado por / contexto:** Railway marcó el despliegue como fallido tras 11
  intentos de healthcheck. Ningún cambio del commit tocaba la base de datos ni
  las librerías.

## Síntoma / reporte

```
ModuleNotFoundError: No module named 'psycopg'
```

La app se caía al arrancar, nunca respondía `/health`, y los 11 intentos de
healthcheck fallaron.

## Diagnóstico (causa raíz)

`requirements.txt` no fijaba **ninguna** versión, así que cada build de Railway
instalaba lo más nuevo de PyPI. El despliegue no se cayó por lo que se programó,
sino por una librería que nadie tocó:

- `sqlalchemy` resolvió a **2.1.0**, que elige el driver `psycopg` (v3) por
  omisión, mientras el proyecto instala `psycopg2-binary`.

El mismo riesgo estaba armado con otra librería, comprobado en local antes de
que estallara:

- `weasyprint` **70.0** eliminó `default_url_fetcher`, que importa
  `app/services/pdf_service.py`. Con esa versión la app tampoco arranca.

Los builds eran irreproducibles: el mismo commit podía desplegar bien un día y
caerse al siguiente.

## Solución

Fijar con `==` todas las dependencias directas en `requirements.txt`, a las
versiones verificadas en local, con un comentario que explica por qué y cómo
subir una versión (cambiarla, correr las pruebas, desplegar).

## Archivos tocados

- `requirements.txt`

## Verificación

Se reprodujo el build de Railway en limpio:

1. Venv nuevo + `pip install -r requirements.txt` → `sqlalchemy 2.0.49`,
   `weasyprint 68.1`, driver resuelto: **psycopg2**.
2. Base Postgres desechable + arranque real con uvicorn: migraciones aplicadas,
   `/health` → `200 {"status":"ok"}`.
3. Las 5 pruebas de `tests/` en verde.

## Prevención (que no reaparezca)

- **REGLA:** toda dependencia en `requirements.txt` va con `==`. Un build sin
  versiones fijas no despliega el commit que se probó, despliega lo que PyPI
  tenga ese día.
- Antes de un despliegue con cambios de arranque o de dependencias: venv limpio,
  instalar desde `requirements.txt` y levantar la app contra una base
  desechable. Es la única prueba que reproduce el fallo de Railway.
- Al subir una versión, hacerlo **de una librería a la vez** y con las pruebas
  en verde.
