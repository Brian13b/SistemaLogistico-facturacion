from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

class VatDetailSchema(BaseModel):
    id: int = Field(..., description="ID del tipo de IVA")
    base_imp: Decimal = Field(..., description="Base imponible")
    importe: Decimal = Field(..., description="Importe del IVA")

class TributeDetailSchema(BaseModel):
    id: int = Field(..., description="ID del tipo de tributo")
    desc: str = Field(..., description="Descripción")
    base_imp: Decimal = Field(..., description="Base imponible")
    alic: Decimal = Field(..., description="Alícuota")
    importe: Decimal = Field(..., description="Importe")

class FacturaRequestSchema(BaseModel):
    """Schema actualizado para RG 4291 v4.1"""
    viaje_id: Optional[int] = None
    sales_point: int = Field(..., ge=1)
    voucher_type: int = Field(..., description="1: Factura A, 6: Factura B, 11: Factura C")
    concept: int = Field(1, ge=1, le=3)
    doc_type: int = Field(80)
    doc_number: str = Field(..., min_length=7, max_length=20)
    
    # Nuevos campos ARCA v4.0/4.1 [cite: 41]
    condicion_iva_receptor_id: Optional[int] = Field(
        None, 
        description="Obligatorio por RG 5616. Consultar FEParamGetCondicionIvaReceptor"
    )
    can_mis_mon_ext: str = Field("N", pattern="^(S|N)$", description="Cancelación Misma Moneda Extranjera")

    # Importes como Decimal
    total_amount: Decimal = Field(..., gt=0)
    net_amount: Decimal = Field(..., ge=0)
    vat_amount: Decimal = Field(0, ge=0)
    non_taxable_amount: Decimal = Field(0, ge=0)
    exempt_amount: Decimal = Field(0, ge=0)
    tributes_amount: Decimal = Field(0, ge=0)
    
    service_start_date: Optional[str] = None
    service_end_date: Optional[str] = None
    payment_due_date: Optional[str] = None
    
    currency: str = Field("PES")
    currency_rate: Decimal = Field(1.0, gt=0)
    
    vat_details: Optional[List[VatDetailSchema]] = None
    tributes_details: Optional[List[TributeDetailSchema]] = None
    
    @validator('service_start_date', 'service_end_date', 'payment_due_date', pre=True)
    def format_date(cls, v):
        if not v: return None
        if isinstance(v, datetime): return v.strftime("%Y%m%d")
        return v.replace("-", "").replace("/", "")

    @validator('total_amount')
    def validate_total(cls, v, values):
        # Validación financiera estricta
        components = [
            values.get('net_amount', 0),
            values.get('vat_amount', 0),
            values.get('non_taxable_amount', 0),
            values.get('exempt_amount', 0),
            values.get('tributes_amount', 0)
        ]
        expected = sum(components)
        if abs(v - expected) > Decimal('0.01'):
            raise ValueError(f"Total ({v}) no coincide con la suma ({expected})")
        return v

class FacturaResponseSchema(BaseModel):
    id: int
    cae: str
    fecha_vto_cae: str
    numero: int
    imp_total: float # Pydantic serializará Decimal a float/string
    estado: str
    pdf_generado: bool
    
    class Config:
        from_attributes = True