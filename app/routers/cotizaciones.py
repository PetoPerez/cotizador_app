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
from app.services.exchange_rate_service import get_usd_mxn
from app import models

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


@router.get("/tipo-cambio")
def tipo_cambio(_=Depends(get_current_user)):
    rate = get_usd_mxn()
    if rate is None:
        raise HTTPException(status_code=503, detail="Tipo de cambio no disponible temporalmente")
    return {"usd_mxn": round(rate, 4)}


def _siguiente_numero(db: Session, empresa: "models.Empresa", vendedor: "models.Usuario") -> str:
    """
    Nuevo formato: AAMMDD-ACRÓNIMO-NUMVEND-CONSECUTIVO
    El consecutivo es histórico por vendedor (incrementa cotizaciones_count del usuario).
    """
    nuevo_count = db.execute(text("""
        UPDATE usuarios
        SET cotizaciones_count = cotizaciones_count + 1
        WHERE id = :uid
        RETURNING cotizaciones_count
    """), {"uid": str(vendedor.id)}).scalar()
    fecha = datetime.now(timezone.utc).strftime("%y%m%d")
    numvend = vendedor.numero_corto if vendedor.numero_corto is not None else 0
    return f"{fecha}-{empresa.acronimo}-{numvend}-{str(nuevo_count).zfill(3)}"


def _cot_options():
    return [
        joinedload(models.Cotizacion.cliente),
        joinedload(models.Cotizacion.vendedor_usuario),
        selectinload(models.Cotizacion.items).joinedload(models.CotizacionItem.producto).selectinload(models.Producto.imagenes),
        selectinload(models.Cotizacion.items).joinedload(models.CotizacionItem.servicio),
    ]


def _ve_todo(usuario: models.Usuario) -> bool:
    """Admin y superadmin ven todas las cotizaciones; los demás solo las suyas."""
    return usuario.rol in ("admin", "superadmin")


@router.get("/", response_model=list[schemas.CotizacionOut])
def listar(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Admin/superadmin ven todo; cada vendedor solo sus propias cotizaciones.
    query = db.query(models.Cotizacion).options(*_cot_options())
    if not _ve_todo(current_user):
        query = query.filter(models.Cotizacion.vendedor_id == current_user.id)
    return query.order_by(models.Cotizacion.created_at.desc()).all()


@router.get("/{id}", response_model=schemas.CotizacionOut)
def obtener(id: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    cot = (db.query(models.Cotizacion)
             .options(*_cot_options())
             .filter(models.Cotizacion.id == id).first())
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if not _ve_todo(current_user) and cot.vendedor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cot


@router.post("/", response_model=list[schemas.CotizacionOut])
def crear(data: schemas.CotizacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La cotización debe tener al menos un ítem")

    # Validar permisos por empresa asignada (admin puede con cualquiera; vendedor solo su empresa)
    empresas_set = set(data.empresas)
    if current_user.rol == "vendedor":
        if current_user.empresa_id is None:
            raise HTTPException(status_code=403, detail="El usuario no tiene una empresa asignada")
        empresa_propia = db.query(models.Empresa).filter(models.Empresa.id == current_user.empresa_id).first()
        if not empresa_propia or empresas_set != {empresa_propia.codigo}:
            raise HTTPException(status_code=403, detail=f"Solo puedes cotizar con la empresa {empresa_propia.codigo if empresa_propia else ''}")

    cliente = db.query(models.Cliente).filter(models.Cliente.id == data.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Usar tipo_cambio del request si viene, sino obtener de API
    if data.tipo_cambio is not None:
        tc = data.tipo_cambio
    else:
        tc = get_usd_mxn()

    cotizaciones_creadas = []

    # Crear una cotización por cada empresa seleccionada
    for empresa_code in data.empresas:
        empresa = db.query(models.Empresa).filter(models.Empresa.codigo == empresa_code).first()
        if not empresa:
            raise HTTPException(status_code=400, detail=f"Empresa '{empresa_code}' no encontrada")

        cotizacion = models.Cotizacion(
            numero_cotizacion=_siguiente_numero(db, empresa, current_user),
            cliente_id=data.cliente_id,
            vendedor_id=current_user.id,
            vendedor_nombre=current_user.nombre,
            vendedor_telefono=current_user.telefono,
            notas=data.notas,
            vigencia=datetime.now(timezone.utc) + timedelta(days=10),
            moneda=data.moneda,
            tipo_cambio=round(tc, 4) if tc else None,
            empresa=empresa_code,
            empresa_id=empresa.id,
            alcance_servicio=data.alcance_servicio,
            tiempo_entrega=data.tiempo_entrega,
            forma_pago=data.forma_pago,
            ciudad_entrega=data.ciudad_entrega,
        )
        db.add(cotizacion)
        db.flush()

        subtotal = 0.0
        for item_data in data.items:
            # Validar que sea producto o servicio (exclusivo)
            if not item_data.producto_id and not item_data.servicio_id:
                raise HTTPException(status_code=400, detail="Cada ítem debe ser producto o servicio")
            if item_data.producto_id and item_data.servicio_id:
                raise HTTPException(status_code=400, detail="Un ítem no puede ser producto y servicio a la vez")

            precio_lista_emp = None
            producto = None
            servicio = None

            empresa_origen_id = None
            if item_data.producto_id:
                producto = db.query(models.Producto).filter(
                    models.Producto.id == item_data.producto_id,
                    models.Producto.activo == True
                ).first()
                if not producto:
                    raise HTTPException(status_code=404, detail=f"Producto {item_data.producto_id} no encontrado")

                # El precio del equipo vive en producto_empresa (uno por empresa).
                # Normalmente se toma de la empresa de la cotización; en Servicios
                # de Lavandería —cuyo catálogo no tiene equipos— el vendedor elige
                # de qué empresa lo toma y se usa ese precio.
                empresa_precio = empresa
                if item_data.empresa_origen_id is not None:
                    if empresa.codigo != 'servicios_lavanderia':
                        # Sin esta guarda, cualquier vendedor podría escoger el
                        # precio más conveniente de otra empresa.
                        raise HTTPException(
                            status_code=400,
                            detail="La empresa de origen solo aplica a cotizaciones de Servicios de Lavandería"
                        )
                    empresa_precio = db.query(models.Empresa).filter(
                        models.Empresa.id == item_data.empresa_origen_id,
                        models.Empresa.activa == True,
                    ).first()
                    if not empresa_precio:
                        raise HTTPException(status_code=400, detail="Empresa de origen no encontrada")
                    empresa_origen_id = empresa_precio.id

                pe = db.query(models.ProductoEmpresa).filter(
                    models.ProductoEmpresa.producto_id == producto.id,
                    models.ProductoEmpresa.empresa_id == empresa_precio.id,
                    models.ProductoEmpresa.activo == True,
                ).first()
                if not pe:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El producto {producto.modelo} no está disponible en la empresa {empresa_precio.nombre}"
                    )
                precio_lista_emp = float(pe.precio_lista)
            else:
                servicio = db.query(models.Servicio).filter(
                    models.Servicio.id == item_data.servicio_id,
                    models.Servicio.activo == True
                ).first()
                if not servicio:
                    raise HTTPException(status_code=404, detail=f"Servicio {item_data.servicio_id} no encontrado")
                # Servicios solo aplican a empresa Servicios de Lavandería
                if empresa.codigo != 'servicios_lavanderia':
                    raise HTTPException(status_code=400, detail="Los servicios solo pueden cotizarse en Servicios de Lavandería")
                precio_lista_emp = float(servicio.precio_unitario)

            # Validar rango de ajuste
            if not (float(current_user.margen_min) <= item_data.porcentaje_ajuste <= float(current_user.margen_max)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Ajuste {item_data.porcentaje_ajuste}% fuera del rango permitido "
                           f"[{current_user.margen_min}%, {current_user.margen_max}%]"
                )

            precio_final = precio_lista_emp * (1 + item_data.porcentaje_ajuste / 100)
            importe = precio_final * item_data.cantidad

            item = models.CotizacionItem(
                cotizacion_id=cotizacion.id,
                producto_id=item_data.producto_id,
                servicio_id=item_data.servicio_id,
                empresa_origen_id=empresa_origen_id,
                descripcion_libre=item_data.descripcion_libre,
                cantidad=item_data.cantidad,
                precio_lista=precio_lista_emp,
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
        cotizaciones_creadas.append(cotizacion)

    db.commit()
    for cot in cotizaciones_creadas:
        db.refresh(cot)
    return cotizaciones_creadas


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
    if not _ve_todo(current_user) and cot.vendedor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    pdf_bytes, img_fallidas = generar_pdf(cot)
    headers = {"Content-Disposition": f"attachment; filename={cot.numero_cotizacion}.pdf"}
    if img_fallidas:
        # El front lee este header para avisar al usuario que el PDF salió con
        # imágenes faltantes y sugerirle contactar a soporte.
        headers["X-Image-Warnings"] = str(img_fallidas)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=headers,
    )