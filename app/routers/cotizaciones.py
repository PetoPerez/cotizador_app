from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import text
import io
from app.database import get_db
from app import schemas
from app.security import get_current_user, require_admin
from app.config import settings
from app.services.pdf_service import generar_pdf
from app import models

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


def _siguiente_numero(db: Session) -> str:
    result = db.execute(text("SELECT nextval('cotizacion_seq')")).scalar()
    año = datetime.now(timezone.utc).strftime("%Y")
    return f"COT-{año}-{str(result).zfill(5)}"


def _cot_options():
    return [
        joinedload(models.Cotizacion.cliente),
        joinedload(models.Cotizacion.vendedor),
        selectinload(models.Cotizacion.items).joinedload(models.CotizacionItem.producto).selectinload(models.Producto.imagenes),
    ]


@router.get("/", response_model=list[schemas.CotizacionOut])
def listar(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    query = db.query(models.Cotizacion).options(*_cot_options())
    if current_user.rol != "admin":
        query = query.filter(models.Cotizacion.vendedor_id == current_user.id)
    return query.order_by(models.Cotizacion.created_at.desc()).all()


@router.get("/{id}", response_model=schemas.CotizacionOut)
def obtener(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    cot = (db.query(models.Cotizacion)
             .options(*_cot_options())
             .filter(models.Cotizacion.id == id).first())
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if current_user.rol != "admin" and str(cot.vendedor_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Sin acceso")
    return cot


@router.post("/", response_model=schemas.CotizacionOut)
def crear(data: schemas.CotizacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La cotización debe tener al menos un ítem")

    cliente = db.query(models.Cliente).filter(models.Cliente.id == data.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cotizacion = models.Cotizacion(
        numero_cotizacion=_siguiente_numero(db),
        cliente_id=data.cliente_id,
        vendedor_id=current_user.id,
        notas=data.notas,
        vigencia=datetime.now(timezone.utc) + timedelta(days=10),
    )
    db.add(cotizacion)
    db.flush()

    subtotal = 0.0
    for item_data in data.items:
        producto = db.query(models.Producto).filter(
            models.Producto.id == item_data.producto_id,
            models.Producto.activo == True
        ).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item_data.producto_id} no encontrado")

        # Validar rango de ajuste
        if not (float(current_user.margen_min) <= item_data.porcentaje_ajuste <= float(current_user.margen_max)):
            raise HTTPException(
                status_code=400,
                detail=f"Ajuste {item_data.porcentaje_ajuste}% fuera del rango permitido "
                       f"[{current_user.margen_min}%, {current_user.margen_max}%]"
            )

        precio_final = float(producto.precio_lista) * (1 + item_data.porcentaje_ajuste / 100)
        importe = precio_final * item_data.cantidad

        item = models.CotizacionItem(
            cotizacion_id=cotizacion.id,
            producto_id=item_data.producto_id,
            cantidad=item_data.cantidad,
            precio_lista=float(producto.precio_lista),
            porcentaje_ajuste=item_data.porcentaje_ajuste,
            precio_final=round(precio_final, 2),
            importe=round(importe, 2),
        )
        db.add(item)
        subtotal += importe

    iva = subtotal * (settings.IVA_PORCENTAJE / 100)
    cotizacion.subtotal = round(subtotal, 2)
    cotizacion.iva = round(iva, 2)
    cotizacion.total = round(subtotal + iva, 2)

    db.commit()
    db.refresh(cotizacion)
    return cotizacion


@router.patch("/{id}/estado")
def cambiar_estado(id: str, data: schemas.CotizacionEstadoUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    estados_validos = {"borrador", "enviada", "aceptada", "cancelada"}
    if data.estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado inválido")
    cot = db.query(models.Cotizacion).filter(models.Cotizacion.id == id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    cot.estado = data.estado
    db.commit()
    return {"detail": f"Estado actualizado a {data.estado}"}


@router.get("/{id}/pdf")
def descargar_pdf(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    cot = db.query(models.Cotizacion).filter(models.Cotizacion.id == id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if current_user.rol != "admin" and str(cot.vendedor_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Sin acceso")

    pdf_bytes = generar_pdf(cot)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={cot.numero_cotizacion}.pdf"}
    )