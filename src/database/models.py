"""
Modelos de base de datos para facturas
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.database import Base


class Factura(Base):
    """Modelo de factura emitida"""
    __tablename__ = "facturas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Datos del comprobante
    tipo_cbte = Column(Integer, nullable=False, index=True)  # 1: Factura A, 6: Factura B, etc.
    punto_vta = Column(Integer, nullable=False, index=True)
    numero = Column(Integer, nullable=False, index=True)
    fecha_cbte = Column(String(8), nullable=False)  # Formato AAAAMMDD
    concepto = Column(Integer, nullable=False)  # 1: Productos, 2: Servicios, 3: Ambos
    
    # Datos del cliente
    tipo_doc = Column(Integer, nullable=False)  # 80: CUIT, 96: DNI, etc.
    nro_doc = Column(String(20), nullable=False, index=True)
    
    # Importes
    imp_total = Column(Float, nullable=False)
    imp_neto = Column(Float, nullable=False)
    imp_iva = Column(Float, default=0)
    imp_trib = Column(Float, default=0)
    imp_op_ex = Column(Float, default=0)
    imp_tot_conc = Column(Float, default=0)
    
    # Datos del CAE
    cae = Column(String(14), nullable=False, unique=True, index=True)
    fecha_vto_cae = Column(String(8), nullable=False)  # Formato AAAAMMDD
    
    # Estado
    estado = Column(String(1), default="A")  # A: Aprobado, R: Rechazado
    observaciones = Column(Text, nullable=True)
    
    # Referencia a viaje (opcional) - sin FK porque la BD de facturación es independiente
    viaje_id = Column(Integer, nullable=True, index=True)
    
    # Trazabilidad
    fecha_creacion = Column(DateTime, default=datetime.now, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Datos adicionales almacenados como JSON
    detalles_iva = Column(Text, nullable=True)  # JSON con detalles de IVA
    detalles_tributos = Column(Text, nullable=True)  # JSON con detalles de tributos
    moneda = Column(String(3), default="PES")
    moneda_cotiz = Column(Float, default=1.0)
    
    # PDF generado
    pdf_generado = Column(Boolean, default=False)
    pdf_path = Column(String(500), nullable=True)


class ParametroAFIP(Base):
    """Modelo para cachear parámetros de AFIP"""
    __tablename__ = "parametros_afip"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False, index=True)  # tipos_comprobante, puntos_venta, etc.
    codigo = Column(String(50), nullable=False, index=True)
    descripcion = Column(String(255), nullable=True)
    datos_adicionales = Column(Text, nullable=True)  # JSON con datos adicionales
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)

