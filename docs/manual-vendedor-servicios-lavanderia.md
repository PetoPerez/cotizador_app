# Manual del vendedor — Servicios de Lavandería (SDL)

Guía para vendedores de **Servicios de Lavandería**. Cubre desde el inicio de
sesión hasta la generación de la cotización, incluyendo lo que hace especial a
SDL: cotizar **servicios**, **equipos** y **ambos combinados**.

> Como vendedor de SDL, tu empresa (**Servicios de Lavandería**) viene
> preseleccionada. A diferencia de los demás vendedores, además de servicios
> puedes cotizar **equipos** (del catálogo de **Supliese**) y **administrar el
> catálogo de servicios**.

---

## 1. Iniciar sesión

1. Abre la dirección del sistema en tu navegador.
2. Captura tu **correo** y **contraseña** y pulsa **Entrar**.
3. Entrarás al panel de **Cotizaciones**.

Para cambiar tu contraseña: menú lateral → **Cambiar contraseña**.

---

## 2. Conocer la pantalla

| Sección | Para qué sirve |
|---|---|
| **Cotizaciones** | Crear cotizaciones y ver tu historial. |
| **Clientes** | Alta y edición de clientes. |
| **Servicios** | Catálogo de servicios de mantenimiento/reparación. |

> Solo ves **tus propias** cotizaciones.

---

## 3. Gestionar el catálogo de servicios

Antes de cotizar, tus servicios deben existir en el catálogo.

1. Menú lateral → **Servicios**.
2. **+ Nuevo servicio** y captura:
   - **Nombre del servicio** (obligatorio) — p. ej. "Mantenimiento preventivo
     lavadora 25kg".
   - **Descripción** — el detalle que aparecerá en el PDF.
   - **Precio unitario (MXN)** (obligatorio).
3. **Guardar**.

- **Buscar** por nombre, **Editar** o **Desactivar** un servicio.
- Los precios de servicios se capturan y manejan **en pesos (MXN)**.

---

## 4. Registrar un cliente

1. Menú lateral → **Clientes** → **+ Nuevo cliente** (o **+ Crear nuevo
   cliente** durante la cotización).
2. Obligatorio: **Nombre o razón social**. Lo demás es opcional pero
   recomendable para un PDF completo.
3. **Guardar**.

---

## 5. Crear una cotización

Menú lateral → **Cotizaciones** → **+ Nueva cotización**.

### 5.1 Cliente
- Búscalo y selecciónalo, o créalo con **+ Crear nuevo cliente**.

### 5.2 Moneda y tipo de cambio
- Por defecto en **dólares (USD)**; puedes cambiar a **MXN** con los botones
  🇲🇽/🇺🇸.
- Tus servicios se guardan en MXN y los equipos en dólares; el sistema
  **convierte todo a la moneda que elijas** de forma automática. El **tipo de
  cambio** viene precargado y es editable.

### 5.3 Empresa
- **Servicios de Lavandería** ya viene preseleccionada.

### 5.4 Agregar servicios, equipos y servicios adicionales
En SDL tienes **tres botones**:

- **+ Agregar servicio** — busca por nombre en tu catálogo de servicios.
- **+ Agregar equipo** — busca un equipo del catálogo de **Supliese**
  (marca, equipo o modelo). Solo se ofrecen equipos de Supliese.
- **+ Servicio adicional** — para cargos **variables que no están en catálogo**
  (flete, maniobras, instalación, etc.).

Puedes **mezclar los tres tipos** en la misma cotización. Para servicios y
equipos:

1. Selecciona el servicio o equipo.
2. Ajusta la **cantidad**.
3. Ajusta el **precio** con el deslizador de **% de ajuste** (dentro de tu
   margen) o escribiendo el **precio unitario**.
4. Quita un renglón con la **×**.

> Los equipos muestran de dónde proviene el precio (Supliese). El precio de
> lista lo define el administrador; tú te mueves dentro de tu margen.

#### Servicios adicionales (flete, maniobras, etc.)
Con **+ Servicio adicional** agregas un renglón **totalmente editable**, sin
catálogo:

1. Escribe la **descripción** (p. ej. "Flete a Guadalajara", "Maniobras de
   descarga").
2. Captura la **cantidad** y el **precio unitario**.
3. Quita el renglón con la **×**.

- No usa deslizador de ajuste: el **precio que capturas es el final**.
- Se captura en la **moneda seleccionada** de la cotización (USD o MXN) y se
  suma al total como cualquier otro renglón.
- En el PDF aparece con la etiqueta **"Servicio adicional"** en la columna de
  marca.

### 5.5 Entrega
- Captura la **Ciudad de entrega**.
- **Tiempo de entrega**: elige una opción (p. ej. *Inmediata*, *15 días
  hábiles*). Aplica a los **equipos**.

### 5.6 Revisar y generar
- El **Resumen** (derecha) muestra Subtotal, IVA (16%) y Total en la moneda
  elegida, en tiempo real.
- Pulsa **Generar cotización**. Se crea y **descarga el PDF automáticamente**.

---

## 6. Cómo se ve el PDF combinado

En una cotización con servicios, equipos y/o servicios adicionales, el PDF
muestra:

- **Alcance del servicio** → aparece **solo si hay servicios**.
- **Tiempo de entrega** → aparece **solo si hay equipos**; en una cotización
  combinada se etiqueta **"TIEMPO DE ENTREGA (EQUIPOS)"** para dejar claro a qué
  aplica.
- La tabla lista juntos los servicios (**Mantenimiento**), los equipos
  (**marca/modelo**) y los cargos variables (**Servicio adicional**).

---

## 7. Tu historial de cotizaciones

En la lista de **Cotizaciones**: número, cliente, total, **estado**, fecha y
vigencia; con tarjetas de resumen arriba.

- **Buscar** y **filtrar por estado**.
- **⬇ PDF** para volver a descargar cualquiera.

Estados: **Borrador → Enviada → Aceptada** (o **Cancelada**). El cambio de
estado lo hace el administrador.

---

## 8. Preguntas frecuentes

**No aparece un equipo al buscar.**
Solo se ofrecen equipos de **Supliese**. Si no está, pídele al administrador que
lo dé de alta en Supliese con su precio.

**No encuentro un servicio.**
Créalo primero en **Servicios**, o revisa que no esté desactivado.

**El total del equipo se ve enorme / muy chico.**
El sistema convierte el precio del equipo (en dólares) a la moneda que elegiste.
Verifica la **moneda** y el **tipo de cambio** en el panel de la derecha.

**¿El servicio cambia de precio con el tipo de cambio?**
Se captura en MXN. Si la cotización está en USD, se muestra convertido a dólares.

**¿Cómo cobro un flete o unas maniobras que no están en catálogo?**
Usa **+ Servicio adicional**: escribe la descripción y el precio. Es un renglón
libre que solo existe en esa cotización; no se guarda en ningún catálogo.

**Cambié la moneda y el precio del servicio adicional se ajustó.**
Es correcto: el sistema mantiene el mismo valor y lo muestra convertido a la
moneda que tengas seleccionada, igual que el resto de los renglones.
