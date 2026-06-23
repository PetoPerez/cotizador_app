from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from app.database import get_db
from app import schemas
from app.security import (
    require_admin, require_superadmin, hash_password,
    verify_password, get_current_user,
)
from app import models

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _es_superadmin(usuario: models.Usuario) -> bool:
    return usuario is not None and usuario.rol == "superadmin"


@router.get("/", response_model=list[schemas.UsuarioOut])
def listar(db: Session = Depends(get_db),
           current_user: models.Usuario = Depends(require_admin)):
    """Lista usuarios. El superadmin nunca aparece para nadie excepto él mismo."""
    query = db.query(models.Usuario).order_by(models.Usuario.nombre)
    if current_user.rol != "superadmin":
        query = query.filter(models.Usuario.rol != "superadmin")
    return query.all()


# ─── Cambio de contraseña por el propio usuario ─────────────────
@router.post("/me/password")
def cambiar_mi_password(
    data: schemas.CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    """Cualquier usuario logueado puede cambiar su propia contraseña sabiendo la actual."""
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if data.password_actual == data.password_nuevo:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta a la actual")
    current_user.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente"}


# ─── Reset de contraseña de otros (solo superadmin) ────────────
@router.post("/{id}/reset-password")
def reset_password(
    id: str,
    data: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_superadmin),
):
    """Resetea la contraseña de cualquier usuario. Solo superadmin."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"detail": f"Contraseña de {usuario.nombre} restablecida"}


@router.post("/", response_model=schemas.UsuarioOut)
def crear(data: schemas.UsuarioCreate, db: Session = Depends(get_db),
          current_user: models.Usuario = Depends(require_admin)):
    if db.query(models.Usuario).filter(models.Usuario.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if data.margen_min > data.margen_max:
        raise HTTPException(status_code=400, detail="margen_min no puede ser mayor que margen_max")

    # Auto-asignar numero_corto si no viene
    numero = data.numero_corto
    if numero is None:
        max_actual = db.query(func.max(models.Usuario.numero_corto)).scalar() or 0
        numero = max_actual + 1

    usuario = models.Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        margen_min=data.margen_min,
        margen_max=data.margen_max,
        empresa_id=data.empresa_id,
        numero_corto=numero,
        telefono=data.telefono,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/{id}", response_model=schemas.UsuarioOut)
def actualizar(id: str, data: schemas.UsuarioUpdate, db: Session = Depends(get_db),
               current_user: models.Usuario = Depends(require_admin)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Solo el superadmin puede modificar a otros superadmins (y a sí mismo)
    if _es_superadmin(usuario) and current_user.rol != "superadmin":
        raise HTTPException(status_code=403, detail="No puedes modificar al superadmin")
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "password":
            setattr(usuario, "password_hash", hash_password(value))
        else:
            setattr(usuario, field, value)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{id}")
def eliminar(id: str, db: Session = Depends(get_db),
             current_user: models.Usuario = Depends(require_admin)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if _es_superadmin(usuario) and current_user.rol != "superadmin":
        raise HTTPException(status_code=403, detail="No puedes desactivar al superadmin")
    usuario.activo = False
    db.commit()
    return {"detail": "Usuario desactivado"}


def _borrar_usuario_definitivo(usuario: models.Usuario, db: Session):
    """Conserva el nombre del vendedor en sus cotizaciones (snapshot) y luego
    elimina al usuario. La FK queda en NULL por ON DELETE SET NULL."""
    db.execute(
        text("""
            UPDATE cotizaciones
            SET vendedor_nombre = :nombre,
                vendedor_telefono = :telefono,
                vendedor_id = NULL
            WHERE vendedor_id = :uid
        """),
        {"nombre": usuario.nombre, "telefono": usuario.telefono, "uid": str(usuario.id)},
    )
    db.delete(usuario)


@router.delete("/{id}/permanente")
def eliminar_permanente(id: str, db: Session = Depends(get_db),
                        current_user: models.Usuario = Depends(require_admin)):
    """Elimina definitivamente un usuario que ya está desactivado.
    Sus cotizaciones se conservan mostrando el nombre del vendedor."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if _es_superadmin(usuario):
        raise HTTPException(status_code=403, detail="No puedes eliminar al superadmin")
    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    if usuario.activo:
        raise HTTPException(status_code=400, detail="Primero desactiva al usuario antes de eliminarlo")
    nombre = usuario.nombre
    _borrar_usuario_definitivo(usuario, db)
    db.commit()
    return {"detail": f"Usuario {nombre} eliminado definitivamente"}


@router.post("/purgar-desactivados")
def purgar_desactivados(db: Session = Depends(get_db),
                        current_user: models.Usuario = Depends(require_admin)):
    """Elimina definitivamente a TODOS los usuarios desactivados.
    El superadmin y el usuario actual nunca se borran."""
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.activo == False,
        models.Usuario.rol != "superadmin",
        models.Usuario.id != current_user.id,
    ).all()
    for usuario in usuarios:
        _borrar_usuario_definitivo(usuario, db)
    db.commit()
    return {"detail": f"{len(usuarios)} usuario(s) desactivado(s) eliminado(s)", "eliminados": len(usuarios)}
