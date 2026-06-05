import io
import uuid
import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app import schemas
from app.security import get_current_user, require_admin
from app import models
from app.services.storage_service import upload_image, delete_image, key_from_url

router = APIRouter(prefix="/productos", tags=["productos"])

# Encabezados aceptados en el Excel (normalizados)
_COL_MAP = {
    "marca":           "marca",
    "equipo":          "equipo",
    "modelo":          "modelo",
    "descripcion":     "descripcion",
    "descripción":     "descripcion",
    "precio de venta": "precio_lista",
    "precio_lista":    "precio_lista",
    "precio lista":    "precio_lista",
}


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


@router.post("/importar")
def importar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
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

    # Detectar encabezados en la primera fila
    headers = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    col_idx = {}
    for i, h in enumerate(headers):
        if h in _COL_MAP:
            col_idx[_COL_MAP[h]] = i

    required = {"marca", "equipo", "modelo", "precio_lista"}
    missing = required - col_idx.keys()
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Columnas requeridas no encontradas: {', '.join(missing)}. "
                   f"Encabezados detectados: {', '.join(h for h in headers if h)}",
        )

    # Empresas de ventas a las que se aplica el import
    empresas_ventas = (db.query(models.Empresa)
                         .filter(models.Empresa.codigo.in_(['clm', 'supliese_gamesail', 'supliese']))
                         .all())

    insertados = 0
    actualizados = 0
    omitidos = 0

    def upsert_precios(producto: models.Producto, precio: float):
        """Upsert producto_empresa para las 3 empresas de ventas con el precio dado."""
        existentes = {str(pe.empresa_id): pe for pe in producto.empresas}
        for emp in empresas_ventas:
            eid = str(emp.id)
            if eid in existentes:
                existentes[eid].precio_lista = precio
                existentes[eid].activo = True
            else:
                db.add(models.ProductoEmpresa(
                    producto_id=producto.id, empresa_id=emp.id,
                    precio_lista=precio, activo=True,
                ))

    for row in rows[1:]:
        def get(field):
            idx = col_idx.get(field)
            return row[idx] if idx is not None and idx < len(row) else None

        marca  = str(get("marca")  or "").strip()
        equipo = str(get("equipo") or "").strip()
        modelo = str(get("modelo") or "").strip()
        desc   = str(get("descripcion") or "").strip() or None
        precio_raw = get("precio_lista")

        if not marca or not equipo or not modelo:
            omitidos += 1
            continue

        try:
            precio = float(str(precio_raw).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            omitidos += 1
            continue

        if precio <= 0:
            omitidos += 1
            continue

        existente = db.query(models.Producto).filter(
            models.Producto.marca   == marca,
            models.Producto.equipo  == equipo,
            models.Producto.modelo  == modelo,
        ).first()

        if existente:
            existente.descripcion = desc
            existente.activo      = True
            db.flush()
            upsert_precios(existente, precio)
            actualizados += 1
        else:
            nuevo = models.Producto(
                marca=marca, equipo=equipo, modelo=modelo,
                descripcion=desc,
            )
            db.add(nuevo)
            db.flush()
            upsert_precios(nuevo, precio)
            insertados += 1

    db.commit()
    return {"insertados": insertados, "actualizados": actualizados, "omitidos": omitidos}


@router.post("/", response_model=schemas.ProductoOut)
def crear(data: schemas.ProductoCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if not data.empresas:
        raise HTTPException(status_code=400, detail="Debes asignar el producto a al menos una empresa")

    producto = models.Producto(
        marca=data.marca, equipo=data.equipo, modelo=data.modelo,
        descripcion=data.descripcion,
    )
    db.add(producto)
    db.flush()  # asigna id

    for pe in data.empresas:
        db.add(models.ProductoEmpresa(
            producto_id=producto.id,
            empresa_id=pe.empresa_id,
            precio_lista=pe.precio_lista,
            activo=pe.activo,
        ))
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{id}", response_model=schemas.ProductoOut)
def actualizar(id: str, data: schemas.ProductoUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
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

        # actualizar / insertar
        for pe in empresas_input:
            eid = str(pe["empresa_id"])
            if eid in existentes:
                existentes[eid].precio_lista = pe["precio_lista"]
                existentes[eid].activo = pe["activo"]
            else:
                db.add(models.ProductoEmpresa(
                    producto_id=producto.id,
                    empresa_id=pe["empresa_id"],
                    precio_lista=pe["precio_lista"],
                    activo=pe["activo"],
                ))
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
