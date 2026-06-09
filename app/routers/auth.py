from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.security import verify_password, create_access_token
from app import models
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(
        models.Usuario.email == data.email,
        models.Usuario.activo == True
    ).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token({"sub": str(user.id), "rol": user.rol})
    empresa_codigo = None
    if user.empresa_id:
        emp = db.query(models.Empresa).filter(models.Empresa.id == user.empresa_id).first()
        empresa_codigo = emp.codigo if emp else None

    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": user.rol,
        "nombre": user.nombre,
        "margen_min": float(user.margen_min),
        "margen_max": float(user.margen_max),
        "empresa_id": str(user.empresa_id) if user.empresa_id else None,
        "empresa_codigo": empresa_codigo,
        "numero_corto": user.numero_corto,
    }