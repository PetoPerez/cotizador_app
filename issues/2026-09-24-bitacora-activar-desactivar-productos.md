# Bitácora de activación/desactivación de productos

- **Fecha:** 2026-09-24
- **Estado:** Abierto
- **Commit(s):** — (pendiente de implementar)
- **Reportado por / contexto:** Peto preguntó quién había borrado el producto
  `GXS-17 / LAVADORA` porque "se perdió el registro". No se pudo responder: nadie
  lo borró, alguien lo desactivó, y **los cambios de `activo` no se registran en
  ningún lado**.

## Síntoma / reporte

Un producto cotizado el 19-sep desapareció del catálogo. La pregunta "¿quién lo
hizo?" no tuvo respuesta posible con los datos que guarda el sistema.

Lo único acotable con evidencia fue:

- Fue una de las tres cuentas con rol admin/superadmin (`PAULINA GOMEZ`,
  `Alfonso Gomez`, `Administrador`), porque el endpoint exige ese rol.
- Ocurrió entre el 19-sep (última cotización que lo usó, luego estaba activo) y
  el 24-sep.

No hay forma de estrecharlo más. Ese es el hueco que cierra esta bitácora.

## Diagnóstico (causa raíz)

`precio_historial` es append-only y registra autor, fecha y origen, pero **solo
de cambios de precio**. El campo `productos.activo` cambia por dos caminos y
ninguno deja rastro:

- `PUT /productos/{id}` con `{"activo": false}` — el botón de la pantalla de
  Productos (`toggleActivo`, `app/templates/productos.html`).
- `DELETE /productos/{id}` — hace soft-delete (`producto.activo = False`), no
  borra la fila. Ningún endpoint de la API borra productos.

Además el problema es recurrente, no aislado: hoy hay **104 productos
inactivos, 21 de ellos con historial de cotizaciones**, y se siguen desactivando
duplicados a mano.

## Solución (instrucción de implementación)

Registrar cada cambio de `activo` con el mismo criterio que ya se usa para los
precios: tabla append-only con snapshot legible, para que el registro sobreviva
aunque el producto o el usuario se borren o se renombren después.

### 1. Modelo — `app/models.py`

Nueva tabla `producto_estado_historial`, calcada de `PrecioHistorial`:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | `server_default=text("gen_random_uuid()")` |
| `producto_id` | UUID FK → `productos.id` | `ondelete="SET NULL"`, nullable |
| `referencia` | Text, **not null** | snapshot `"MARCA / EQUIPO / MODELO"` |
| `activo_nuevo` | Boolean, not null | `True` = activación, `False` = desactivación |
| `usuario_id` | UUID FK → `usuarios.id` | `ondelete="SET NULL"`, nullable |
| `usuario_nombre` | String(100) | snapshot del autor |
| `origen` | String(20), not null | `manual` \| `importacion` \| `script` |
| `created_at` | DateTime(timezone=True) | `default=now_utc` |

### 2. Migración — `app/main.py`

Agregar el `CREATE TABLE IF NOT EXISTS` al bloque de arranque, junto al de
`producto_imagenes` (mismo estilo, sin Alembic).

### 3. Registro — `app/routers/productos.py`

Crear un helper al lado de `registrar_cambio_precio` (usar `ref_producto` para
la referencia, sin el sufijo de empresa) y llamarlo **solo cuando el valor
cambia de verdad**, comparando contra el estado previo, para no llenar la tabla
de repeticiones:

- en `actualizar()` (`PUT`), cuando el payload trae `activo` distinto al actual;
- en `eliminar()` (`DELETE`), cuando el producto estaba activo.

El `origen` se toma del canal: `manual` en ambos endpoints.

### 4. Consulta — endpoint y pantalla

- `GET /productos/{id}/historial-estado`, solo admin, ordenado por fecha
  descendente.
- En la pantalla de Productos, mostrar el último movimiento ("Desactivado por
  PAULINA GOMEZ el 24-sep") en la fila de un producto inactivo, o al pie del
  modal de edición. Esa fila ya se puede ver: el listado acepta
  `?incluir_inactivos=true` desde el fix del 2026-09-24.

### 5. Prueba

Un `tests/test_estado_historial.py` con asserts, al estilo de
`tests/test_productos_inactivos.py`: la función que decide si hay que registrar
devuelve `True` solo cuando el valor cambia, y `False` cuando el `PUT` reenvía el
mismo `activo` o no lo trae.

### Fuera de alcance (decidir aparte)

- **Trigger en Postgres que bloquee `DELETE` sobre `productos`.** Hoy la API no
  borra, pero cualquiera con acceso directo a la base de Railway sí puede, y
  `producto_empresa` e `imagenes` se irían en cascada. Es el otro candado
  propuesto y sigue pendiente.
- Aplicar la misma bitácora a `servicios`, `clientes` y `usuarios`.

## Archivos tocados

Pendiente. Previstos: `app/models.py`, `app/main.py`, `app/routers/productos.py`,
`app/templates/productos.html`, `tests/test_estado_historial.py`.

## Verificación

Con la implementación lista:

1. Desactivar un producto de prueba desde la pantalla y confirmar que aparece un
   renglón con el usuario correcto, fecha y `activo_nuevo = false`.
2. Reactivarlo y confirmar el segundo renglón.
3. Guardar el producto sin tocar la casilla y confirmar que **no** se registra
   nada.
4. Confirmar que un vendedor no puede consultar el historial (403).

## Prevención (que no reaparezca)

- **REGLA:** todo campo que esconda información del usuario (`activo`,
  `estado`, `visible`) necesita bitácora de quién lo cambió. Un borrado suave sin
  registro no es trazabilidad, es un borrado lento.
- El registro guarda **snapshot legible** (`referencia`, `usuario_nombre`), no
  solo llaves foráneas: las FK se ponen en NULL al borrar y el rastro se perdería
  justo en el caso que interesa investigar.
