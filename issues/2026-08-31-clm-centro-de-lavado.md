# «CLM centro de lavado» no aparece en el listado de productos

- **Fecha:** 2026-08-31
- **Estado:** En espera (del modelo exacto que busca el reportante)
- **Commit(s):** — (investigación, sin cambios de código)
- **Reportado por / contexto:** un equipo que "debe aparecer como CLM centro de lavado" no sale en el listado; el usuario consultó y no había match.

## Síntoma / reporte
No aparece en el listado de productos un equipo esperado como "CLM centro de lavado".

## Diagnóstico (consulta de solo lectura a la BD de producción, Railway)
- **NO existe** ningún producto con marca **CLM** + equipo **Centro de lavado**
  (ni activo ni inactivo). Búsqueda exacta y aproximada: 0 resultados.
- Sí existen **12 "Centro de lavado"** (todos activos, disponibles en la empresa
  CLM), pero de marca **KINGSTAR / LG / MAYTAG / SUPLIESE** — ninguno marca CLM.
- La marca **CLM** tiene **25 productos** activos: Lavadora(s), Secadora(s),
  Planchadora de Rodillos, Plegadora — **ninguno "Centro de lavado"**.
- Los 46 inactivos con "lavado" son GIRBAU/GAMESAIL/WHIRLPOOL/MAYTAG — ninguno
  "CLM centro de lavado".

**Por qué "no hay match":** el buscador del listado
(`app/routers/productos.py`) compara el texto **campo por campo**
(`modelo` OR `marca` OR `equipo`), no la frase concatenada. Buscar la frase
completa "CLM centro de lavado" nunca coincide, aunque "CLM" y "centro de lavado"
existan por separado. (Además, el buscador no incluye `descripcion`.)

## Solución (pendiente de dato)
El producto simplemente **no está capturado**. Opciones, cuando llegue el modelo:
1. Si debe existir como tal → **darlo de alta** (marca/equipo/modelo/precio por
   empresa), con confirmación (escribe en producción).
2. Si el equipo buscado es uno de los 12 "Centro de lavado" existentes → ya está
   en CLM; buscarlo por "centro de lavado" (no "CLM centro de lavado").
3. Posible causa raíz: el centro de lavado de CLM se capturó como *Lavadora* o
   *Secadora* → revisar los 25 productos CLM para reclasificar.

**Decisión (2026-08-31):** esperar el **modelo exacto** antes de crear nada, para
evitar duplicados/reclasificaciones erróneas.

## Prevención (que no reaparezca)
- Mejora futura posible: que el buscador tolere frases combinadas (tokenizar el
  `q` y hacer AND por token sobre marca+equipo+modelo) para que "CLM centro de
  lavado" encuentre coincidencias parciales.
