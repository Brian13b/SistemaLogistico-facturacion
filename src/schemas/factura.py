"""
Schemas Pydantic para la API de facturación
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class VatDetailSchema(BaseModel):
    """Schema para detalle de IVA"""
    id: int = Field(..., description="ID del tipo de IVA")
    base_imp: float = Field(..., description="Base imponible")
    importe: float = Field(..., description="Importe del IVA")


class TributeDetailSchema(BaseModel):
    """Schema para detalle de tributo"""
    id: int = Field(..., description="ID del tipo de tributo")
    desc: str = Field(..., description="Descripción del tributo")
    base_imp: float = Field(..., description="Base imponible")
    alic: float = Field(..., description="Alícuota")
    importe: float = Field(..., description="Importe del tributo")


class FacturaRequestSchema(BaseModel):
    """Schema para solicitar una factura"""
    viaje_id: Optional[int] = Field(None, description="ID del viaje asociado")
    sales_point: int = Field(..., description="Punto de venta", ge=1)
    voucher_type: int = Field(..., description="Tipo de comprobante (1: Factura A, 6: Factura B)")
    concept: int = Field(1, description="Concepto (1: Productos, 2: Servicios, 3: Ambos)", ge=1, le=3)
    doc_type: int = Field(80, description="Tipo de documento (80: CUIT, 96: DNI, etc.)")
    doc_number: str = Field(..., description="Número de documento", min_length=7, max_length=20)
    total_amount: float = Field(..., description="Importe total", gt=0)
    net_amount: float = Field(..., description="Importe neto gravado", ge=0)
    vat_amount: float = Field(0, description="Importe de IVA", ge=0)
    non_taxable_amount: float = Field(0, description="Importe no gravado", ge=0)
    exempt_amount: float = Field(0, description="Importe exento", ge=0)
    tributes_amount: float = Field(0, description="Importe de tributos", ge=0)
    service_start_date: Optional[str] = Field(None, description="Fecha de inicio del servicio (AAAAMMDD)")
    service_end_date: Optional[str] = Field(None, description="Fecha de fin del servicio (AAAAMMDD)")
    payment_due_date: Optional[str] = Field(None, description="Fecha de vencimiento del pago (AAAAMMDD)")
    currency: str = Field("PES", description="Moneda (PES: Pesos argentinos)")
    currency_rate: float = Field(1.0, description="Cotización de la moneda", gt=0)
    vat_details: Optional[List[VatDetailSchema]] = Field(None, description="Detalles de IVA")
    tributes_details: Optional[List[TributeDetailSchema]] = Field(None, description="Detalles de tributos")
    
    @validator('service_start_date', 'service_end_date', 'payment_due_date', pre=True)
    def format_date(cls, v):
        """Formatea las fechas al formato requerido por AFIP"""
        if v is None:
            return None
        
        if isinstance(v, datetime):
            return v.strftime("%Y%m%d")
        
        if isinstance(v, str):
            # Si ya está en formato AAAAMMDD
            if len(v) == 8 and v.isdigit():
                return v
            
            # Intentar convertir desde otros formatos
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(v, fmt).strftime("%Y%m%d")
                except ValueError:
                    continue
            
            raise ValueError(f"Formato de fecha no reconocido: {v}")
        
        raise ValueError(f"Tipo de fecha no soportado: {type(v)}")
    
    @validator('total_amount')
    def validate_total(cls, v, values):
        """Valida que el total sea consistente con los componentes"""
        if 'net_amount' in values and 'vat_amount' in values:
            net = values.get('net_amount', 0)
            vat = values.get('vat_amount', 0)
            non_tax = values.get('non_taxable_amount', 0)
            exempt = values.get('exempt_amount', 0)
            tributes = values.get('tributes_amount', 0)
            
            expected_total = net + vat + non_tax + exempt + tributes
            
            # Permitir pequeñas diferencias por redondeo
            if abs(v - expected_total) > 0.01:
                raise ValueError(f"El importe total ({v}) no coincide con la suma de componentes ({expected_total})")
        
        return v


class FacturaResponseSchema(BaseModel):
    """Schema para respuesta de factura generada"""
    id: int
    viaje_id: Optional[int]
    tipo_cbte: int
    punto_vta: int
    numero: int
    fecha_cbte: str
    cae: str
    fecha_vto_cae: str
    estado: str
    imp_total: float
    imp_neto: float
    imp_iva: float
    tipo_doc: int
    nro_doc: str
    observaciones: Optional[str]
    fecha_creacion: datetime
    pdf_generado: bool
    
    class Config:
        from_attributes = True


class FacturaListSchema(BaseModel):
    """Schema simplificado para listar facturas"""
    id: int
    tipo_cbte: int
    punto_vta: int
    numero: int
    fecha_cbte: str
    cae: str
    imp_total: float
    nro_doc: str
    estado: str
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True


class ParametroAFIPSchema(BaseModel):
    """Schema para parámetros de AFIP"""
    tipo: str
    codigo: str
    descripcion: Optional[str]
    datos_adicionales: Optional[Dict[str, Any]]


class FacturaConsultaSchema(BaseModel):
    """Schema para consultar una factura específica"""
    tipo_cbte: int
    punto_vta: int
    numero: int

