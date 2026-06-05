from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app import schemas, models

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("/", response_model=list[schemas.EmpresaOut])
def listar(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (db.query(models.Empresa)
              .filter(models.Empresa.activa == True)
              .order_by(models.Empresa.nombre).all())
