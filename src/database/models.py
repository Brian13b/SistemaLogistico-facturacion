from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric, Float
from datetime import datetime
from src.database.database import Base

class Factura(Base):
    __tablename__ = "facturas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Datos del comprobante
    tipo_cbte = Column(Integer, nullable=False, index=True)
    punto_vta = Column(Integer, nullable=False, index=True)
    numero = Column(Integer, nullable=False, index=True)
    fecha_cbte = Column(String(8), nullable=False)
    concepto = Column(Integer, nullable=False)
    
    # Datos del cliente
    tipo_doc = Column(Integer, nullable=False)
    nro_doc = Column(String(20), nullable=False, index=True)
    condicion_iva_receptor_id = Column(Integer, nullable=True) 
    
    # Importes
    cantidad = Column(Float, default=1.0)
    unidad_medida = Column(String(50), default="Unidad")
    precio_unitario = Column(Float, default=0.0)
    alicuota_iva = Column(Float, default=21.0)
    imp_total = Column(Numeric(15, 2), nullable=False)
    imp_neto = Column(Numeric(15, 2), nullable=False)
    imp_iva = Column(Numeric(15, 2), default=0)
    imp_trib = Column(Numeric(15, 2), default=0)
    imp_op_ex = Column(Numeric(15, 2), default=0)
    imp_tot_conc = Column(Numeric(15, 2), default=0)
    
    # Datos del CAE
    cae = Column(String(14), nullable=False, unique=True, index=True)
    fecha_vto_cae = Column(String(8), nullable=False)
    
    # Estado
    estado = Column(String(1), default="A")
    observaciones = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    
    # Referencias
    viaje_id = Column(Integer, nullable=True, index=True)
    
    # Trazabilidad
    fecha_creacion = Column(DateTime, default=datetime.now, nullable=False)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Datos adicionales
    detalles_iva = Column(Text, nullable=True)
    detalles_tributos = Column(Text, nullable=True)
    moneda = Column(String(3), default="PES")
    moneda_cotiz = Column(Numeric(10, 6), default=1.0)
    can_mis_mon_ext = Column(String(1), default="N") 
    
    pdf_generado = Column(Boolean, default=False)
    pdf_path = Column(String(500), nullable=True)

class ParametroAFIP(Base):
    __tablename__ = "parametros_afip"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False, index=True)
    codigo = Column(String(50), nullable=False, index=True)
    descripcion = Column(String(255), nullable=True)
    datos_adicionales = Column(Text, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)

