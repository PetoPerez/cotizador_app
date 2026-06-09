from uuid import UUID
from datetime import datetime
from typing import Optional, List, Literal
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
    empresa_id: Optional[UUID] = None
    empresa_codigo: Optional[str] = None
    numero_corto: Optional[int] = None


# ---------- Usuario ----------
class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    rol: str = Field("vendedor", pattern="^(admin|vendedor)$")
    margen_min: float = Field(-5.0, ge=-100, le=0)
    margen_max: float = Field(5.0, ge=0, le=100)
    empresa_id: Optional[UUID] = None
    numero_corto: Optional[int] = Field(None, ge=0, le=9999)
    telefono: Optional[str] = Field(None, max_length=30)

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    rol: Optional[str] = Field(None, pattern="^(admin|vendedor)$")
    margen_min: Optional[float] = Field(None, ge=-100, le=0)
    margen_max: Optional[float] = Field(None, ge=0, le=100)
    activo: Optional[bool] = None
    empresa_id: Optional[UUID] = None
    numero_corto: Optional[int] = Field(None, ge=0, le=9999)
    telefono: Optional[str] = Field(None, max_length=30)

class UsuarioOut(BaseModel):
    id: UUID
    nombre: str
    email: str
    rol: str
    margen_min: float
    margen_max: float
    activo: bool
    empresa_id: Optional[UUID] = None
    numero_corto: Optional[int] = None
    cotizaciones_count: Optional[int] = 0
    telefono: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Cliente ----------
class ClienteCreate(BaseModel):
    nombre_razon_social: str = Field(..., min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=150)
    atencion_titulo: Optional[str] = Field(None, max_length=20)
    atencion_nombre: Optional[str] = Field(None, max_length=150)
    ciudad: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=100)
    pais: Optional[str] = Field('México', max_length=100)
    rfc: Optional[str] = Field(None, max_length=20)
    domicilio_empresa: Optional[str] = None
    domicilio_entrega: Optional[str] = None
    dias_contacto: Optional[str] = Field(None, max_length=100)
    horario_contacto: Optional[str] = Field(None, max_length=50)
    relacion: Optional[str] = Field(None, max_length=100)
    cargo_ocupa: Optional[str] = Field(None, max_length=100)

class ClienteUpdate(BaseModel):
    nombre_razon_social: Optional[str] = Field(None, min_length=1, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=150)
    atencion_titulo: Optional[str] = Field(None, max_length=20)
    atencion_nombre: Optional[str] = Field(None, max_length=150)
    ciudad: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=100)
    pais: Optional[str] = Field(None, max_length=100)
    rfc: Optional[str] = Field(None, max_length=20)
    domicilio_empresa: Optional[str] = None
    domicilio_entrega: Optional[str] = None
    dias_contacto: Optional[str] = Field(None, max_length=100)
    horario_contacto: Optional[str] = Field(None, max_length=50)
    relacion: Optional[str] = Field(None, max_length=100)
    cargo_ocupa: Optional[str] = Field(None, max_length=100)

class ClienteOut(BaseModel):
    id: UUID
    nombre_razon_social: str
    telefono: Optional[str]
    email: Optional[str]
    atencion_titulo: Optional[str] = None
    atencion_nombre: Optional[str] = None
    ciudad: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None
    rfc: Optional[str] = None
    domicilio_empresa: Optional[str] = None
    domicilio_entrega: Optional[str] = None
    dias_contacto: Optional[str] = None
    horario_contacto: Optional[str] = None
    relacion: Optional[str] = None
    cargo_ocupa: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Empresa ----------
class EmpresaOut(BaseModel):
    id: UUID
    codigo: str
    acronimo: str
    nombre: str
    nombre_corto: Optional[str] = None
    activa: bool

    model_config = {"from_attributes": True}


# ---------- Producto ----------
class ProductoEmpresaInput(BaseModel):
    empresa_id: UUID
    precio_lista: float = Field(..., gt=0, lt=10_000_000)
    activo: bool = True

class ProductoEmpresaOut(BaseModel):
    empresa_id: UUID
    precio_lista: float
    activo: bool

    model_config = {"from_attributes": True}


class ProductoCreate(BaseModel):
    marca: str = Field(..., min_length=1, max_length=100)
    equipo: str = Field(..., min_length=1, max_length=100)
    modelo: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=2000)
    empresas: List[ProductoEmpresaInput] = Field(default_factory=list)

class ProductoUpdate(BaseModel):
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    equipo: Optional[str] = Field(None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=2000)
    activo: Optional[bool] = None
    empresas: Optional[List[ProductoEmpresaInput]] = None

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
    precio_lista: Optional[float] = None  # legacy/fallback
    imagen_url: Optional[str] = None
    imagenes: List[ProductoImagenOut] = []
    empresas: List[ProductoEmpresaOut] = []
    activo: bool

    model_config = {"from_attributes": True}


# ---------- Servicio ----------
class ServicioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)
    precio_unitario: float = Field(..., gt=0, lt=10_000_000)

class ServicioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=2000)
    precio_unitario: Optional[float] = Field(None, gt=0, lt=10_000_000)
    activo: Optional[bool] = None

class ServicioOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: Optional[str]
    precio_unitario: float
    activo: bool

    model_config = {"from_attributes": True}


# ---------- Cotización ----------
class CotizacionItemCreate(BaseModel):
    producto_id: Optional[UUID] = None
    servicio_id: Optional[UUID] = None
    descripcion_libre: Optional[str] = None
    cantidad: int
    porcentaje_ajuste: float = 0.0

class CotizacionItemOut(BaseModel):
    id: UUID
    producto_id: Optional[UUID] = None
    servicio_id: Optional[UUID] = None
    descripcion_libre: Optional[str] = None
    cantidad: int
    precio_lista: float
    porcentaje_ajuste: float
    precio_final: float
    importe: float
    producto: Optional[ProductoOut] = None
    servicio: Optional[ServicioOut] = None

    model_config = {"from_attributes": True}

class CotizacionCreate(BaseModel):
    cliente_id: UUID
    items: List[CotizacionItemCreate]
    notas: Optional[str] = None
    moneda: str = Field('MXN', pattern='^(MXN|USD)$')
    tipo_cambio: Optional[float] = None
    empresas: List[Literal['clm', 'supliese_gamesail', 'supliese', 'servicios_lavanderia']] = Field(default=['clm'])
    alcance_servicio: Optional[str] = None
    tiempo_entrega: Optional[str] = Field(None, max_length=50)
    forma_pago: Optional[str] = Field(None, max_length=150)
    ciudad_entrega: Optional[str] = Field(None, max_length=150)

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
    moneda: str
    tipo_cambio: Optional[float] = None
    empresa: str
    fecha: datetime
    vigencia: Optional[datetime]
    items: List[CotizacionItemOut]
    alcance_servicio: Optional[str] = None
    tiempo_entrega: Optional[str] = None
    forma_pago: Optional[str] = None
    ciudad_entrega: Optional[str] = None

    model_config = {"from_attributes": True}

class CotizacionEstadoUpdate(BaseModel):
    estado: str
