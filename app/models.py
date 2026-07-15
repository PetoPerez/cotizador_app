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
    margen_min = Column(Numeric(5, 2), nullable=False, default=-5.00)
    margen_max = Column(Numeric(5, 2), nullable=False, default=5.00)
    activo = Column(Boolean, nullable=False, default=True)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    numero_corto = Column(Integer, unique=True)
    cotizaciones_count = Column(Integer, nullable=False, default=0)
    telefono = Column(String(30))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizaciones = relationship("Cotizacion", back_populates="vendedor_usuario")
    empresa = relationship("Empresa")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_razon_social = Column(String(200), nullable=False)
    telefono = Column(String(30))
    email = Column(String(150))
    atencion_titulo = Column(String(20))
    atencion_nombre = Column(String(150))
    ciudad = Column(String(100))
    estado = Column(String(100))
    pais = Column(String(100), default='México')
    rfc = Column(String(20))
    domicilio_empresa = Column(Text)
    domicilio_entrega = Column(Text)
    dias_contacto = Column(String(100))
    horario_contacto = Column(String(50))
    relacion = Column(String(100))
    cargo_ocupa = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizaciones = relationship("Cotizacion", back_populates="cliente")


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String(30), nullable=False, unique=True)
    acronimo = Column(String(10), nullable=False, unique=True)
    nombre = Column(String(200), nullable=False)
    nombre_corto = Column(String(50))
    direccion = Column(Text)
    rfc = Column(String(20))
    telefono = Column(String(30))
    email = Column(String(150))
    logo_url = Column(Text)
    logo_decoracion_url = Column(Text)
    template_pdf = Column(String(100))
    activa = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class ProductoEmpresa(Base):
    __tablename__ = "producto_empresa"

    producto_id = Column(UUID(as_uuid=True), ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), primary_key=True)
    precio_lista = Column(Numeric(12, 2), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    producto = relationship("Producto")
    empresa = relationship("Empresa")


class ProductoImagen(Base):
    __tablename__ = "producto_imagenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id = Column(UUID(as_uuid=True), ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    producto = relationship("Producto", back_populates="imagenes")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marca = Column(String(100), nullable=False)
    equipo = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    precio_lista = Column(Numeric(12, 2), nullable=True)  # legacy: precio por empresa vive en producto_empresa
    imagen_url = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    imagenes = relationship("ProductoImagen", back_populates="producto",
                            order_by=ProductoImagen.orden, cascade="all, delete-orphan")
    empresas = relationship("ProductoEmpresa", cascade="all, delete-orphan", overlaps="producto,empresa")


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_cotizacion = Column(String(30), nullable=False, unique=True)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    # vendedor_id es nullable: si el usuario se elimina, queda NULL pero se conserva
    # el nombre/teléfono en las columnas snapshot de abajo (ON DELETE SET NULL).
    vendedor_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    # Snapshot del vendedor al momento de crear la cotización, para preservar el
    # nombre en el historial/PDF aunque el usuario sea eliminado.
    vendedor_nombre = Column(String(100))
    vendedor_telefono = Column(String(30))
    estado = Column(String(20), nullable=False, default="borrador")
    notas = Column(Text)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    iva = Column(Numeric(14, 2), nullable=False, default=0)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    fecha = Column(DateTime(timezone=True), default=now_utc)
    vigencia = Column(DateTime(timezone=True))
    moneda = Column(String(3), nullable=False, default='MXN')
    tipo_cambio = Column(Numeric(10, 4), nullable=True)
    empresa = Column(String(30), nullable=False, default='clm')  # legacy: clm, supliese_gamesail, supliese, supliese_gomez
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"))
    alcance_servicio = Column(Text)
    tiempo_entrega = Column(String(50))
    forma_pago = Column(String(150))
    ciudad_entrega = Column(String(150))
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cliente = relationship("Cliente", back_populates="cotizaciones")
    vendedor_usuario = relationship("Usuario", back_populates="cotizaciones")
    empresa_rel = relationship("Empresa", foreign_keys=[empresa_id])
    items = relationship("CotizacionItem", back_populates="cotizacion", cascade="all, delete-orphan")

    @property
    def vendedor(self):
        """Devuelve el usuario vendedor si aún existe; si fue eliminado, un
        objeto con el nombre/teléfono conservados en el snapshot. Así las
        plantillas y la API siguen usando `cot.vendedor.nombre` sin cambios."""
        if self.vendedor_usuario is not None:
            return self.vendedor_usuario
        return _VendedorSnapshot(self.vendedor_nombre, self.vendedor_telefono)


class _VendedorSnapshot:
    """Vendedor histórico (usuario ya eliminado). Expone solo lo que usan las
    plantillas y el esquema de salida: nombre y teléfono."""
    def __init__(self, nombre, telefono):
        self.nombre = nombre or "Usuario eliminado"
        self.telefono = telefono


class PrecioHistorial(Base):
    """Registro append-only de cada cambio de precio (productos por empresa y
    servicios). Guarda un snapshot legible (`referencia`, `usuario_nombre`) para
    conservar la trazabilidad aunque el producto, la empresa o el usuario se
    eliminen o renombren después."""
    __tablename__ = "precio_historial"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String(10), nullable=False)  # 'producto' | 'servicio'
    # Referencias opcionales (ON DELETE SET NULL); el snapshot de abajo preserva
    # la información aunque estas filas desaparezcan.
    producto_id = Column(UUID(as_uuid=True), ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    servicio_id = Column(UUID(as_uuid=True), ForeignKey("servicios.id", ondelete="SET NULL"), nullable=True)
    # Snapshot legible: "MARCA / EQUIPO / MODELO — ACRONIMO" o el nombre del servicio.
    referencia = Column(Text, nullable=False)
    precio_anterior = Column(Numeric(12, 2), nullable=True)  # NULL cuando es un alta
    precio_nuevo = Column(Numeric(12, 2), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_nombre = Column(String(100))  # snapshot del autor del cambio
    origen = Column(String(20), nullable=False, default="manual")  # canal del cambio: manual | importacion | script (un alta se reconoce por precio_anterior NULL)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class CotizacionItem(Base):
    __tablename__ = "cotizacion_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cotizacion_id = Column(UUID(as_uuid=True), ForeignKey("cotizaciones.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(UUID(as_uuid=True), ForeignKey("productos.id"), nullable=True)
    servicio_id = Column(UUID(as_uuid=True), ForeignKey("servicios.id"), nullable=True)
    descripcion_libre = Column(Text)
    cantidad = Column(Integer, nullable=False)
    precio_lista = Column(Numeric(12, 2), nullable=False)
    porcentaje_ajuste = Column(Numeric(5, 2), nullable=False, default=0)
    precio_final = Column(Numeric(12, 2), nullable=False)
    importe = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    cotizacion = relationship("Cotizacion", back_populates="items")
    producto = relationship("Producto")
    servicio = relationship("Servicio")
