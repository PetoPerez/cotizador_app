from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


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
    nombre: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    rol: str = Field("vendedor", pattern="^(admin|vendedor)$")
    margen_min: float = Field(-10.0, ge=-100, le=0)
    margen_max: float = Field(10.0, ge=0, le=100)

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    rol: Optional[str] = Field(None, pattern="^(admin|vendedor)$")
    margen_min: Optional[float] = Field(None, ge=-100, le=0)
    margen_max: Optional[float] = Field(None, ge=0, le=100)
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
    nombre_razon_social: str = Field(..., min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=150)

class ClienteUpdate(BaseModel):
    nombre_razon_social: Optional[str] = Field(None, min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=150)

class ClienteOut(BaseModel):
    id: UUID
    nombre_razon_social: str
    telefono: Optional[str]
    email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Producto ----------
class ProductoCreate(BaseModel):
    marca: str = Field(..., min_length=1, max_length=100)
    equipo: str = Field(..., min_length=1, max_length=100)
    modelo: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=2000)
    precio_lista: float = Field(..., gt=0, lt=10_000_000)

class ProductoUpdate(BaseModel):
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    equipo: Optional[str] = Field(None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=2000)
    precio_lista: Optional[float] = Field(None, gt=0, lt=10_000_000)
    activo: Optional[bool] = None

class ProductoImagenOut(BaseModel):
    id: UUID
    url: str
    orden: int

    model_config = {"from_attributes": True}

class ProductoOut(BaseModel):
    id: UUID
    marca: str
    equipo: str
    modelo: str
    descripcion: Optional[str]
    precio_lista: float
    imagen_url: Optional[str] = None
    imagenes: List[ProductoImagenOut] = []
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
