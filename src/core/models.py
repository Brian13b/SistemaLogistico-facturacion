"""
Modelos de datos para el sistema de facturación
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator

class VatDetail(BaseModel):
    """Detalle de IVA"""
    Id: int = Field(..., description="ID del tipo de IVA (5: 21%, 4: 10.5%, etc.)")
    BaseImp: float = Field(..., description="Base imponible")
    Importe: float = Field(..., description="Importe del IVA")

class TributeDetail(BaseModel):
    """Detalle de tributo"""
    Id: int = Field(..., description="ID del tipo de tributo")
    Desc: str = Field(..., description="Descripción del tributo")
    BaseImp: float = Field(..., description="Base imponible")
    Alic: float = Field(..., description="Alícuota")
    Importe: float = Field(..., description="Importe del tributo")

class InvoiceRequest(BaseModel):
    """Datos para la solicitud de factura"""
    sales_point: int = Field(..., description="Punto de venta")
    voucher_type: int = Field(..., description="Tipo de comprobante (1: Factura A, etc.)")
    concept: int = Field(1, description="Concepto (1: Productos, 2: Servicios, 3: Ambos)")
    doc_type: int = Field(80, description="Tipo de documento (80: CUIT, etc.)")
    doc_number: str = Field(..., description="Número de documento")
    total_amount: float = Field(..., description="Importe total")
    net_amount: float = Field(..., description="Importe neto gravado")
    vat_amount: float = Field(..., description="Importe de IVA")
    non_taxable_amount: float = Field(0, description="Importe no gravado")
    exempt_amount: float = Field(0, description="Importe exento")
    tributes_amount: float = Field(0, description="Importe de tributos")
    service_start_date: Optional[str] = Field(None, description="Fecha de inicio del servicio (AAAAMMDD)")
    service_end_date: Optional[str] = Field(None, description="Fecha de fin del servicio (AAAAMMDD)")
    payment_due_date: Optional[str] = Field(None, description="Fecha de vencimiento del pago (AAAAMMDD)")
    currency: str = Field("PES", description="Moneda (PES: Pesos argentinos)")
    currency_rate: float = Field(1.0, description="Cotización de la moneda")
    vat_details: Optional[List[VatDetail]] = Field(None, description="Detalles de IVA")
    tributes_details: Optional[List[TributeDetail]] = Field(None, description="Detalles de tributos")
    condicion_iva_receptor_id: Optional[int] = None
    can_mis_mon_ext: str = "N"
    
    @validator('service_start_date', 'service_end_date', 'payment_due_date', pre=True)
    def format_date(cls, v):
        """Formatea las fechas al formato requerido por AFIP"""
        if v is None:
            return None
        
        if isinstance(v, datetime):
            return v.strftime("%Y%m%d")
        
        if isinstance(v, str):
            if len(v) == 8 and v.isdigit():
                return v
            
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(v, fmt).strftime("%Y%m%d")
                except ValueError:
                    continue
            
            raise ValueError(f"Formato de fecha no reconocido: {v}")
        
        raise ValueError(f"Tipo de fecha no soportado: {type(v)}")

class InvoiceResponse(BaseModel):
    """Respuesta de factura autorizada"""
    cae: str = Field(..., description="CAE (Código de Autorización Electrónico)")
    cae_expiration: str = Field(..., description="Fecha de vencimiento del CAE")
    voucher_number: int = Field(..., description="Número de comprobante")
    voucher_date: str = Field(..., description="Fecha del comprobante")
    status: str = Field("A", description="Estado (A: Aprobado)")
    observations: Optional[List[str]] = Field(None, description="Observaciones")
    errors: Optional[List[str]] = Field(None, description="Errores")
    
    @property
    def is_approved(self):
        """Indica si la factura fue aprobada"""
        return self.status == "A" and self.cae and not self.errors

class AfipAuth(BaseModel):
    """Datos de autenticación para AFIP"""
    token: str
    sign: str
    cuit: str
    expiration: datetime
    
    @property
    def is_valid(self):
        """Indica si la autenticación es válida"""
        return datetime.now() < self.expiration