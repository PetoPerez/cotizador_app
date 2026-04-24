from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.security import get_current_user
from app import models

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.get("/", response_model=list[schemas.ClienteOut])
def listar(q: str = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    query = db.query(models.Cliente)
    if q:
        query = query.filter(models.Cliente.nombre_razon_social.ilike(f"%{q}%"))
    return query.order_by(models.Cliente.nombre_razon_social).all()

@router.post("/", response_model=schemas.ClienteOut)
def crear(data: schemas.ClienteCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cliente = models.Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente

@router.put("/{id}", response_model=schemas.ClienteOut)
def actualizar(id: str, data: schemas.ClienteUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cliente, field, value)
    db.commit()
    db.refresh(cliente)
    return cliente