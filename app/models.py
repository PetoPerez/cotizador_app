import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Numeric, Integer,
    Text, ForeignKey, DateTime, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    rol = Column(String(20), nullable=False, default="vendedor")
    margen_min = Column(Numeric(5, 2), nullable=False, default=-10.00)
    margen_max = Column(Numeric(5, 2), nullable=False, default=10.00)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizaciones = relationship("Cotizacion", back_populates="vendedor")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_razon_social = Column(String(200), nullable=False)
    telefono = Column(String(30))
    email = Column(String(150))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizaciones = relationship("Cotizacion", back_populates="cliente")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marca = Column(String(100), nullable=False)
    equipo = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    precio_lista = Column(Numeric(12, 2), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_cotizacion = Column(String(30), nullable=False, unique=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    vendedor_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    estado = Column(String(20), nullable=False, default="borrador")
    notas = Column(Text)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    iva = Column(Numeric(14, 2), nullable=False, default=0)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    fecha = Column(DateTime(timezone=True), default=now_utc)
    vigencia = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cliente = relationship("Cliente", back_populates="cotizaciones")
    vendedor = relationship("Usuario", back_populates="cotizaciones")
    items = relationship("CotizacionItem", back_populates="cotizacion", cascade="all, delete-orphan")


class CotizacionItem(Base):
    __tablename__ = "cotizacion_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cotizacion_id = Column(UUID(as_uuid=True), ForeignKey("cotizaciones.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(UUID(as_uuid=True), ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_lista = Column(Numeric(12, 2), nullable=False)
    porcentaje_ajuste = Column(Numeric(5, 2), nullable=False, default=0)
    precio_final = Column(Numeric(12, 2), nullable=False)
    importe = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizacion = relationship("Cotizacion", back_populates="items")
    producto = relationship("Producto")
