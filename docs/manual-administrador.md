# Manual del administrador

Guía completa para administradores del sistema de cotizaciones. Incluye el
manejo de usuarios, clientes y reportes, con **énfasis en la carga y el manejo
de productos y servicios**, que es el corazón del sistema.

> El administrador ve **todas** las cotizaciones de **todas** las empresas y
> tiene acceso a los apartados exclusivos: Productos, Servicios, Reportes y
> Usuarios.

---

## 1. Iniciar sesión

1. Abre la dirección del sistema, captura tu **correo** y **contraseña**, y
   pulsa **Entrar**.
2. Menú lateral completo:

| Sección | Para qué sirve |
|---|---|
| **Cotizaciones** | Ver todas las cotizaciones y cambiar su estado. |
| **Clientes** | Alta y edición de clientes. |
| **Productos** | Catálogo de equipos y sus precios por empresa. |
| **Servicios** | Catálogo de servicios de lavandería. |
| **Reportes** | Inventario y auditoría de cambios de precio. |
| **Usuarios** | Alta y administración de vendedores y admins. |

---

## 2. Conceptos clave del catálogo

Antes de cargar productos, entiende el modelo de precios:

- Un **producto** (equipo) tiene: **marca**, **equipo**, **modelo** y
  **descripción**.
- El **precio no es único**: cada producto tiene **un precio por empresa**
  (CLM, Gamesail, Supliese, Girbau). El mismo equipo puede costar distinto en
  cada una.
- Un producto solo puede cotizarse en las empresas a las que esté **asignado
  con precio**.
- Los **servicios** (catálogo de Servicios de Lavandería) son aparte y tienen
  un **precio unitario en MXN**.
- Los precios de **equipos** se manejan en **dólares (USD)**; los de
  **servicios**, en **pesos (MXN)**.

---

## 3. Productos — carga y manejo (apartado clave)

Menú lateral → **Productos**. Verás el catálogo con imagen, marca, equipo,
modelo, descripción, **precios por empresa** y estado.

Tienes **tres formas** de cargar productos:

### 3.1 Alta individual (**+ Nuevo producto**)

1. Pulsa **+ Nuevo producto**.
2. Captura **Marca**, **Equipo**, **Modelo** y **Descripción**.
3. En **Disponibilidad y precio por empresa (MXN)**:
   - **Marca la casilla** de cada empresa en la que se ofrecerá el producto.
   - Captura su **precio** para esa empresa.
   - Las empresas **sin marcar no ofrecen** el producto al cotizar.
4. **Guardar**. Debes asignar al menos una empresa.

### 3.2 Carga masiva por Excel (recomendada para muchos productos)

1. Pulsa **⬇ Plantilla Excel** para descargar la plantilla con los encabezados
   correctos y una fila de ejemplo.
2. Llena la plantilla. Columnas:
   - **marca**, **equipo**, **modelo**, **descripcion** (marca y descripción
     son opcionales; equipo y modelo son obligatorios).
   - **precio_general**: si lo llenas, el producto queda disponible en **todas**
     las empresas a ese precio.
   - **precio_clm**, **precio_gs**, **precio_sup**, **precio_gir**: precio por
     empresa concreta (pisa al general para esa empresa).
   - **precio_servicios**: crea/actualiza un ítem en el **catálogo de
     Servicios** usando el modelo como nombre.
   - Llena **solo los precios que apliquen**; deja en blanco los demás.
3. Pulsa **⬆ Importar Excel** y selecciona tu archivo.
4. El sistema informa cuántos productos se **insertaron**, **actualizaron** y
   **omitieron**, y cuántos **precios** y **servicios** se aplicaron.

> **Productos sin marca**: si una fila no trae marca, el sistema pide
> **confirmación** antes de guardarla como "General". Puedes aceptar o cancelar
> la importación completa.

> La importación es **idempotente**: si un producto ya existe (misma marca,
> equipo y modelo) se **actualizan sus precios** en lugar de duplicarlo.

### 3.3 Editar, imágenes y baja

- **Editar**: cambia datos o precios por empresa; también puedes **desmarcar**
  una empresa para dejar de ofrecer ahí el producto.
- **Imágenes**: abre la galería del producto para **agregar** varias imágenes o
  **eliminarlas**. La primera imagen se usa como principal en el PDF.
- **Desactivar**: da de baja un producto (deja de aparecer al cotizar). No se
  borra: conserva su historial.
- **Buscar** por marca, equipo, modelo o descripción; puedes **filtrar por
  empresa**.

> **Equipos en Servicios de Lavandería**: SDL puede cotizar equipos, pero solo
> del catálogo de **Supliese**. Para que un equipo esté disponible para SDL,
> asígnalo a **Supliese** con su precio.

---

## 4. Servicios — carga y manejo

Menú lateral → **Servicios** (catálogo de Servicios de Lavandería).

1. **+ Nuevo servicio** y captura:
   - **Nombre del servicio** (obligatorio).
   - **Descripción** (aparece en el PDF).
   - **Precio unitario (MXN)** (obligatorio).
2. **Guardar**.

- **Buscar** por nombre, **Editar** o **Desactivar**.
- También puedes crear/actualizar servicios de forma **masiva** con la columna
  **precio_servicios** de la plantilla de productos (ver 3.2).
- Los servicios los pueden gestionar el **administrador** y los **vendedores de
  Servicios de Lavandería**.

---

## 5. Usuarios

Menú lateral → **Usuarios**.

1. **+ Nuevo usuario** y captura:
   - **Nombre**, **Email**, **Teléfono**, **Contraseña** (mínimo 6 caracteres).
   - **Rol**: *Vendedor* o *Admin*.
   - **# vendedor**: número corto para la numeración de sus cotizaciones (o
     "Auto").
   - **Empresa asignada**: **solo para vendedores** (define con qué empresa
     cotizan). Los admins no requieren empresa.
   - **Margen mínimo / máximo (%)**: rango en el que ese vendedor puede ajustar
     precios (por defecto −5% / +5%).
2. **Guardar**.

- **Resetear contraseña** de un usuario.
- **Desactivar** un usuario (sus cotizaciones se conservan con el nombre
  histórico). Con **Eliminar desactivados** depuras los que ya no usas.

> Para habilitar un **vendedor de Servicios de Lavandería**, crea un vendedor y
> asígnale la empresa **Servicios de Lavandería**.

---

## 6. Cotizaciones (vista de administrador)

- Ves **todas** las cotizaciones de todas las empresas.
- **⬇ PDF** para descargar cualquiera.
- **Estado**: botón para cambiar el estado (Borrador → Enviada → Aceptada →
  Cancelada). *Este cambio es exclusivo del administrador.*
- También puedes **crear cotizaciones** con cualquier empresa (el selector te
  muestra todas las empresas, no una preseleccionada).

---

## 7. Reportes

Menú lateral → **Reportes** (solo administrador).

### 7.1 Reporte de inventario
- Descarga en **Excel** el catálogo de productos con una **columna de precio por
  cada empresa** y su estado. Opción para incluir productos desactivados.

### 7.2 Auditoría de cambios de precio
- Registro de **quién cambió qué precio y cuándo**: precio anterior, precio
  nuevo, autor, fecha y **origen** (manual, importación o script).
- **Filtra** por tipo (producto/servicio), origen, fechas o texto, y **exporta a
  Excel**.
- El historial es **prospectivo**: registra los cambios a partir de su
  activación.

---

## 8. Buenas prácticas

- **Carga masiva** para altas grandes; usa la **plantilla** para no equivocar
  encabezados.
- Mantén los **precios por empresa** al día: son los que ven los vendedores.
- Define **márgenes** por vendedor con criterio: acota cuánto pueden mover el
  precio.
- Antes de cotizar equipos en SDL, verifica que estén asignados a **Supliese**.
- Usa la **auditoría de precios** para revisar cambios y responsables.
- **Desactiva** en lugar de borrar: conservas el historial.
