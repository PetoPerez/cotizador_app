from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.security import require_admin, hash_password
from app import models

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("/", response_model=list[schemas.UsuarioOut])
def listar(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(models.Usuario).order_by(models.Usuario.nombre).all()

@router.post("/", response_model=schemas.UsuarioOut)
def crear(data: schemas.UsuarioCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(models.Usuario).filter(models.Usuario.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if data.margen_min > data.margen_max:
        raise HTTPException(status_code=400, detail="margen_min no puede ser mayor que margen_max")
    usuario = models.Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        margen_min=data.margen_min,
        margen_max=data.margen_max,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.put("/{id}", response_model=schemas.UsuarioOut)
def actualizar(id: str, data: schemas.UsuarioUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "password":
            setattr(usuario, "password_hash", hash_password(value))
        else:
            setattr(usuario, field, value)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.delete("/{id}")
def eliminar(id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = False
    db.commit()
    return {"detail": "Usuario desactivado"}