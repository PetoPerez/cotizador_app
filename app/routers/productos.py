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
def listar(q: str = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = (db.query(models.Producto)
               .options(selectinload(models.Producto.imagenes))
               .filter(models.Producto.activo == True))
    if q:
        query = query.filter(
            models.Producto.modelo.ilike(f"%{q}%") |
            models.Producto.marca.ilike(f"%{q}%") |
            models.Producto.equipo.ilike(f"%{q}%")
        )
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

    insertados = 0
    actualizados = 0
    omitidos = 0

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
            existente.precio_lista = precio
            existente.descripcion  = desc
            existente.activo       = True
            actualizados += 1
        else:
            db.add(models.Producto(
                marca=marca, equipo=equipo, modelo=modelo,
                descripcion=desc, precio_lista=precio,
            ))
            insertados += 1

    db.commit()
    return {"insertados": insertados, "actualizados": actualizados, "omitidos": omitidos}


@router.post("/", response_model=schemas.ProductoOut)
def crear(data: schemas.ProductoCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    producto = models.Producto(**data.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{id}", response_model=schemas.ProductoOut)
def actualizar(id: str, data: schemas.ProductoUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    producto = db.query(models.Producto).filter(models.Producto.id == id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(producto, field, value)
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
