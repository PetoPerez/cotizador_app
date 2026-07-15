import io
import uuid
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app import schemas
from app.security import get_current_user, require_admin
from app import models
from app.services.storage_service import upload_image, delete_image, key_from_url
from app.services.precio_audit import registrar_cambio_precio, ref_producto

router = APIRouter(prefix="/productos", tags=["productos"])

# Encabezados base del Excel (normalizados a lowercase)
_COL_BASE = {
    "marca":       "marca",
    "equipo":      "equipo",
    "modelo":      "modelo",
    "descripcion": "descripcion",
    "descripción": "descripcion",
}


def _empresas_para_import(db: Session) -> list[models.Empresa]:
    """Empresas que aceptan productos importables (todas excepto servicios_lavanderia)."""
    return (db.query(models.Empresa)
              .filter(models.Empresa.codigo != 'servicios_lavanderia',
                      models.Empresa.activa == True)
              .order_by(models.Empresa.nombre)
              .all())


@router.get("/", response_model=list[schemas.ProductoOut])
def listar(
    q: str = None,
    empresa: str = None,  # filtro opcional: código de empresa (clm, supliese_gamesail, etc.)
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = (db.query(models.Producto)
               .options(selectinload(models.Producto.imagenes),
                        selectinload(models.Producto.empresas))
               .filter(models.Producto.activo == True))
    if q:
        query = query.filter(
            models.Producto.modelo.ilike(f"%{q}%") |
            models.Producto.marca.ilike(f"%{q}%") |
            models.Producto.equipo.ilike(f"%{q}%")
        )
    if empresa:
        empresa_obj = db.query(models.Empresa).filter(models.Empresa.codigo == empresa).first()
        if empresa_obj:
            query = (query.join(models.ProductoEmpresa,
                                models.ProductoEmpresa.producto_id == models.Producto.id)
                          .filter(models.ProductoEmpresa.empresa_id == empresa_obj.id,
                                  models.ProductoEmpresa.activo == True))
    return query.order_by(models.Producto.marca, models.Producto.equipo).all()


@router.get("/plantilla-importar")
def descargar_plantilla(db: Session = Depends(get_db), _=Depends(require_admin)):
    """Descarga un Excel vacío con los encabezados correctos para importar productos."""
    empresas = _empresas_para_import(db)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"

    # Encabezados base + precio_general + una columna por empresa + precio_servicios
    headers = ["marca", "equipo", "modelo", "descripcion", "precio_general"]
    for emp in empresas:
        headers.append(f"precio_{emp.acronimo.lower()}")
    headers.append("precio_servicios")

    # Estilo encabezado
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="26326E", end_color="26326E", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")

    for col_idx, name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        ws.column_dimensions[cell.column_letter].width = 18

    # Fila de ejemplo: producto normal con precio por empresa
    ejemplo = ["GIRBAU", "Lavadora industrial", "HS-6028", "Capacidad 28kg, motor inverter", ""]
    for emp in empresas:
        ejemplo.append(75000)
    ejemplo.append("")  # precio_servicios
    for col_idx, val in enumerate(ejemplo, start=1):
        ws.cell(row=2, column=col_idx, value=val)

    # Instrucciones
    nota = ("Llena solo los precios que apliquen. · precio_general: el producto queda "
            "disponible para TODAS las empresas a ese precio (si dejas la marca vacía se "
            "pone 'General'). · precio_servicios: crea el ítem en el catálogo de Servicios "
            "de Lavandería (usa el modelo como nombre).")
    ws.cell(row=3, column=1, value=nota)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=len(headers))
    ws.cell(row=3, column=1).font = Font(italic=True, color="808080")
    ws.cell(row=3, column=1).alignment = Alignment(horizontal="left")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plantilla_productos.xlsx"'},
    )


@router.post("/importar")
def importar_excel(
    file: UploadFile = File(...),
    marca_general: bool = False,  # confirmación: guardar productos sin marca como 'General'
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin),
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx o .xls")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file.file.read()), data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo Excel")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    empresas = _empresas_para_import(db)  # CLM, GS, SUP, GIR (sin servicios)
    # Mapeo: "precio_<acronimo>" → empresa
    precio_col_to_empresa = {f"precio_{e.acronimo.lower()}": e for e in empresas}

    # Detectar encabezados en la primera fila
    headers = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    col_idx = {}                # campo base → índice
    precio_col_idx = {}         # codigo empresa → índice
    idx_general = None          # columna precio_general (todas las empresas)
    idx_servicios = None        # columna precio_servicios (catálogo de servicios)
    for i, h in enumerate(headers):
        if h in _COL_BASE:
            col_idx[_COL_BASE[h]] = i
        elif h == "precio_general":
            idx_general = i
        elif h in ("precio_servicios", "precio_sdl"):
            idx_servicios = i
        elif h in precio_col_to_empresa:
            precio_col_idx[precio_col_to_empresa[h].codigo] = i

    required_base = {"equipo", "modelo"}  # marca es opcional (se rellena con 'General')
    missing = required_base - col_idx.keys()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Columnas requeridas no encontradas: {', '.join(missing)}. "
                   f"Encabezados detectados: {', '.join(h for h in headers if h)}",
        )
    if not precio_col_idx and idx_general is None and idx_servicios is None:
        raise HTTPException(
            status_code=400,
            detail="Debes incluir al menos una columna de precio "
                   "(precio_general, precio_clm, precio_gs, precio_sup, precio_gir o precio_servicios). "
                   f"Encabezados detectados: {', '.join(h for h in headers if h)}",
        )

    empresas_por_codigo = {e.codigo: e for e in empresas}

    insertados = 0
    actualizados = 0
    omitidos = 0
    precios_aplicados = 0
    servicios_creados = 0
    servicios_actualizados = 0
    sin_marca = 0   # productos cuya marca venía vacía (se guardan como 'General')
    detalles = []  # motivos de las filas omitidas

    def upsert_precio(producto: models.Producto, empresa: models.Empresa, precio: float):
        """Upsert un único producto_empresa con el precio dado."""
        existentes = {str(pe.empresa_id): pe for pe in producto.empresas}
        eid = str(empresa.id)
        if eid in existentes:
            anterior = existentes[eid].precio_lista
            existentes[eid].precio_lista = precio
            existentes[eid].activo = True
        else:
            anterior = None
            db.add(models.ProductoEmpresa(
                producto_id=producto.id, empresa_id=empresa.id,
                precio_lista=precio, activo=True,
            ))
        registrar_cambio_precio(
            db, tipo="producto", referencia=ref_producto(producto, empresa),
            precio_nuevo=precio, precio_anterior=anterior,
            producto_id=producto.id, empresa_id=empresa.id,
            usuario=current_user, origen="importacion",
        )

    def upsert_servicio(nombre: str, descripcion, precio: float):
        """Crea o actualiza un ítem del catálogo de Servicios de Lavandería."""
        s = db.query(models.Servicio).filter(models.Servicio.nombre == nombre).first()
        if s:
            anterior = s.precio_unitario
            s.precio_unitario = precio
            s.activo = True
            db.flush()
            registrar_cambio_precio(
                db, tipo="servicio", referencia=nombre, precio_nuevo=precio,
                precio_anterior=anterior, servicio_id=s.id,
                usuario=current_user, origen="importacion",
            )
            return "actualizado"
        nuevo = models.Servicio(nombre=nombre, descripcion=descripcion,
                                precio_unitario=precio, activo=True)
        db.add(nuevo)
        db.flush()
        registrar_cambio_precio(
            db, tipo="servicio", referencia=nombre, precio_nuevo=precio,
            servicio_id=nuevo.id, usuario=current_user, origen="importacion",
        )
        return "creado"

    def parsear_precio(raw):
        if raw is None or raw == "":
            return None
        try:
            v = float(str(raw).replace(",", "").replace("$", "").strip())
            return v if v > 0 else None
        except (ValueError, TypeError):
            return None

    try:
        for n, row in enumerate(rows[1:], start=2):
            def cell(idx):
                return row[idx] if idx is not None and idx < len(row) else None

            marca_raw = str(cell(col_idx.get("marca")) or "").strip()
            sin_marca_fila = (marca_raw == "")
            marca  = marca_raw or "General"
            equipo = str(cell(col_idx.get("equipo")) or "").strip()
            modelo = str(cell(col_idx.get("modelo")) or "").strip()
            desc   = str(cell(col_idx.get("descripcion")) or "").strip() or None

            # Fila en blanco: se ignora en silencio
            if not equipo and not modelo:
                continue
            if not equipo or not modelo:
                omitidos += 1
                detalles.append(f"Fila {n}: falta equipo o modelo")
                continue

            # Precio para el catálogo de servicios
            precio_svc = parsear_precio(cell(idx_servicios)) if idx_servicios is not None else None

            # Precios de producto por empresa
            precios_fila = {}  # codigo empresa → precio
            if idx_general is not None:
                pg = parsear_precio(cell(idx_general))
                if pg is not None:
                    for e in empresas:  # disponible para TODAS las empresas
                        precios_fila[e.codigo] = pg
            for codigo, idx in precio_col_idx.items():
                p = parsear_precio(cell(idx))
                if p is not None:
                    precios_fila[codigo] = p  # un precio por empresa pisa al general

            if not precios_fila and precio_svc is None:
                omitidos += 1
                detalles.append(f"Fila {n} ({modelo or marca}): sin ningún precio válido")
                continue

            # ── Servicio de lavandería ──
            if precio_svc is not None:
                if upsert_servicio(modelo, desc, precio_svc) == "creado":
                    servicios_creados += 1
                else:
                    servicios_actualizados += 1

            # ── Producto ──
            if precios_fila:
                if sin_marca_fila:
                    sin_marca += 1
                    detalles.append(f"Fila {n} ({modelo}): sin marca → se guardará como 'General'")
                existente = db.query(models.Producto).filter(
                    models.Producto.marca  == marca,
                    models.Producto.equipo == equipo,
                    models.Producto.modelo == modelo,
                ).first()
                if existente:
                    db.flush()
                    for codigo, precio in precios_fila.items():
                        upsert_precio(existente, empresas_por_codigo[codigo], precio)
                        precios_aplicados += 1
                    actualizados += 1
                else:
                    nuevo = models.Producto(marca=marca, equipo=equipo, modelo=modelo, descripcion=desc)
                    db.add(nuevo)
                    db.flush()
                    for codigo, precio in precios_fila.items():
                        upsert_precio(nuevo, empresas_por_codigo[codigo], precio)
                        precios_aplicados += 1
                    insertados += 1

        # Si hay productos sin marca y el usuario aún no confirmó, NO se guarda
        # nada: se devuelve una vista previa para que acepte o cancele.
        if sin_marca > 0 and not marca_general:
            db.rollback()
            return {
                "requiere_confirmacion": True,
                "sin_marca": sin_marca,
                "insertados": insertados,
                "actualizados": actualizados,
                "omitidos": omitidos,
                "precios_aplicados": precios_aplicados,
                "servicios_creados": servicios_creados,
                "servicios_actualizados": servicios_actualizados,
                "detalles": detalles[:50],
            }

        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error procesando el archivo: {ex}")

    return {
        "requiere_confirmacion": False,
        "sin_marca": sin_marca,
        "insertados": insertados,
        "actualizados": actualizados,
        "omitidos": omitidos,
        "precios_aplicados": precios_aplicados,
        "servicios_creados": servicios_creados,
        "servicios_actualizados": servicios_actualizados,
        "detalles": detalles[:50],
    }


@router.post("/", response_model=schemas.ProductoOut)
def crear(data: schemas.ProductoCreate, db: Session = Depends(get_db),
          current_user: models.Usuario = Depends(require_admin)):
    if not data.empresas:
        raise HTTPException(status_code=400, detail="Debes asignar el producto a al menos una empresa")

    producto = models.Producto(
        marca=data.marca, equipo=data.equipo, modelo=data.modelo,
        descripcion=data.descripcion,
    )
    db.add(producto)
    db.flush()  # asigna id

    empresas_map = {str(e.id): e for e in db.query(models.Empresa)
                    .filter(models.Empresa.id.in_([pe.empresa_id for pe in data.empresas])).all()}
    for pe in data.empresas:
        db.add(models.ProductoEmpresa(
            producto_id=producto.id,
            empresa_id=pe.empresa_id,
            precio_lista=pe.precio_lista,
            activo=pe.activo,
        ))
        emp = empresas_map.get(str(pe.empresa_id))
        if emp:
            registrar_cambio_precio(
                db, tipo="producto", referencia=ref_producto(producto, emp),
                precio_nuevo=pe.precio_lista, producto_id=producto.id,
                empresa_id=pe.empresa_id, usuario=current_user, origen="manual",
            )
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{id}", response_model=schemas.ProductoOut)
def actualizar(id: str, data: schemas.ProductoUpdate, db: Session = Depends(get_db),
               current_user: models.Usuario = Depends(require_admin)):
    producto = db.query(models.Producto).filter(models.Producto.id == id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    payload = data.model_dump(exclude_none=True)
    empresas_input = payload.pop("empresas", None)

    for field, value in payload.items():
        setattr(producto, field, value)

    if empresas_input is not None:
        # Reemplazar mapping producto_empresa con lo recibido
        existentes = {str(pe.empresa_id): pe for pe in producto.empresas}
        nuevos_ids = {str(pe["empresa_id"]) for pe in empresas_input}
        empresas_map = {str(e.id): e for e in db.query(models.Empresa)
                        .filter(models.Empresa.id.in_([pe["empresa_id"] for pe in empresas_input])).all()}

        # actualizar / insertar
        for pe in empresas_input:
            eid = str(pe["empresa_id"])
            if eid in existentes:
                anterior = existentes[eid].precio_lista
                existentes[eid].precio_lista = pe["precio_lista"]
                existentes[eid].activo = pe["activo"]
            else:
                anterior = None
                db.add(models.ProductoEmpresa(
                    producto_id=producto.id,
                    empresa_id=pe["empresa_id"],
                    precio_lista=pe["precio_lista"],
                    activo=pe["activo"],
                ))
            emp = empresas_map.get(eid)
            if emp:
                registrar_cambio_precio(
                    db, tipo="producto", referencia=ref_producto(producto, emp),
                    precio_nuevo=pe["precio_lista"], precio_anterior=anterior,
                    producto_id=producto.id, empresa_id=pe["empresa_id"],
                    usuario=current_user, origen="manual",
                )
        # eliminar los que ya no vienen
        for eid, pe in existentes.items():
            if eid not in nuevos_ids:
                db.delete(pe)

    db.commit()
    db.refresh(producto)
    return producto


@router.post("/{id}/imagen", response_model=schemas.ProductoOut)
async def subir_imagen(
    id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    producto = db.query(models.Producto).filter(models.Producto.id == id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos de imagen")

    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    imagen_id = str(uuid.uuid4())
    key = f"productos/{id}/{imagen_id}.{ext}"
    content = await file.read()

    try:
        url = upload_image(content, key, file.content_type or "image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir imagen: {e}")

    orden = db.query(models.ProductoImagen).filter(models.ProductoImagen.producto_id == id).count()
    db.add(models.ProductoImagen(producto_id=id, url=url, orden=orden))
    if orden == 0:
        producto.imagen_url = url
    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{id}/imagen/{imagen_id}")
def eliminar_imagen(
    id: str,
    imagen_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    imagen = db.query(models.ProductoImagen).filter(
        models.ProductoImagen.id == imagen_id,
        models.ProductoImagen.producto_id == id,
    ).first()
    if not imagen:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    try:
        delete_image(key_from_url(imagen.url))
    except Exception:
        pass

    db.delete(imagen)

    producto = db.query(models.Producto).filter(models.Producto.id == id).first()
    restantes = (db.query(models.ProductoImagen)
                 .filter(models.ProductoImagen.producto_id == id)
                 .order_by(models.ProductoImagen.orden).all())
    producto.imagen_url = restantes[0].url if restantes else None
    db.commit()
    return {"detail": "Imagen eliminada"}


@router.delete("/{id}")
def eliminar(id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    producto = db.query(models.Producto).filter(models.Producto.id == id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto.activo = False
    db.commit()
    return {"detail": "Producto desactivado"}
