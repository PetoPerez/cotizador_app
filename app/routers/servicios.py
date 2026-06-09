from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas, models
from app.security import get_current_user

router = APIRouter(prefix="/servicios", tags=["servicios"])


def _require_sdl_o_admin(user: models.Usuario, db: Session):
    """Solo admin o vendedor asignado a Servicios de Lavandería pueden gestionar."""
    if user.rol == "admin":
        return
    if user.rol == "vendedor" and user.empresa_id:
        emp = db.query(models.Empresa).filter(models.Empresa.id == user.empresa_id).first()
        if emp and emp.codigo == "servicios_lavanderia":
            return
    raise HTTPException(status_code=403, detail="Solo admin o vendedores de Servicios de Lavandería pueden gestionar servicios")


@router.get("/", response_model=list[schemas.ServicioOut])
def listar(q: str = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = db.query(models.Servicio).filter(models.Servicio.activo == True)
    if q:
        query = query.filter(models.Servicio.nombre.ilike(f"%{q}%"))
    return query.order_by(models.Servicio.nombre).all()


@router.post("/", response_model=schemas.ServicioOut)
def crear(data: schemas.ServicioCreate, db: Session = Depends(get_db),
          current_user: models.Usuario = Depends(get_current_user)):
    _require_sdl_o_admin(current_user, db)
    servicio = models.Servicio(
        nombre=data.nombre,
        descripcion=data.descripcion,
        precio_unitario=data.precio_unitario,
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio


@router.put("/{id}", response_model=schemas.ServicioOut)
def actualizar(id: str, data: schemas.ServicioUpdate, db: Session = Depends(get_db),
               current_user: models.Usuario = Depends(get_current_user)):
    _require_sdl_o_admin(current_user, db)
    servicio = db.query(models.Servicio).filter(models.Servicio.id == id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(servicio, field, value)
    db.commit()
    db.refresh(servicio)
    return servicio


@router.delete("/{id}")
def eliminar(id: str, db: Session = Depends(get_db),
             current_user: models.Usuario = Depends(get_current_user)):
    _require_sdl_o_admin(current_user, db)
    servicio = db.query(models.Servicio).filter(models.Servicio.id == id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    servicio.activo = False
    db.commit()
    return {"detail": "Servicio desactivado"}
