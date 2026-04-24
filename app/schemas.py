from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    margen_min: float
    margen_max: float


# ---------- Usuario ----------
class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: str = "vendedor"
    margen_min: float = -10.0
    margen_max: float = 10.0

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[str] = None
    margen_min: Optional[float] = None
    margen_max: Optional[float] = None
    activo: Optional[bool] = None

class UsuarioOut(BaseModel):
    id: UUID
    nombre: str
    email: str
    rol: str
    margen_min: float
    margen_max: float
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Cliente ----------
class ClienteCreate(BaseModel):
    nombre_razon_social: str
    telefono: Optional[str] = None
    email: Optional[str] = None

class ClienteUpdate(BaseModel):
    nombre_razon_social: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class ClienteOut(BaseModel):
    id: UUID
    nombre_razon_social: str
    telefono: Optional[str]
    email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Producto ----------
class ProductoCreate(BaseModel):
    marca: str
    equipo: str
    modelo: str
    descripcion: Optional[str] = None
    precio_lista: float

class ProductoUpdate(BaseModel):
    marca: Optional[str] = None
    equipo: Optional[str] = None
    modelo: Optional[str] = None
    descripcion: Optional[str] = None
    precio_lista: Optional[float] = None
    activo: Optional[bool] = None

class ProductoOut(BaseModel):
    id: UUID
    marca: str
    equipo: str
    modelo: str
    descripcion: Optional[str]
    precio_lista: float
    activo: bool

    model_config = {"from_attributes": True}


# ---------- Cotización ----------
class CotizacionItemCreate(BaseModel):
    producto_id: UUID
    cantidad: int
    porcentaje_ajuste: float = 0.0

class CotizacionItemOut(BaseModel):
    id: UUID
    producto_id: UUID
    cantidad: int
    precio_lista: float
    porcentaje_ajuste: float
    precio_final: float
    importe: float
    producto: ProductoOut

    model_config = {"from_attributes": True}

class CotizacionCreate(BaseModel):
    cliente_id: UUID
    items: List[CotizacionItemCreate]
    notas: Optional[str] = None

class CotizacionOut(BaseModel):
    id: UUID
    numero_cotizacion: str
    cliente: ClienteOut
    vendedor: UsuarioOut
    estado: str
    notas: Optional[str]
    subtotal: float
    iva: float
    total: float
    fecha: datetime
    vigencia: Optional[datetime]
    items: List[CotizacionItemOut]

    model_config = {"from_attributes": True}

class CotizacionEstadoUpdate(BaseModel):
    estado: str
