from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator, model_validator

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

    @model_validator(mode='after')
    def validate_total_consistency(self) -> 'FacturaRequestSchema':
        """Valida que el importe total sea la suma exacta de sus componentes."""
        
        # Aseguramos que los valores sean Decimal
        net = self.net_amount or Decimal(0)
        vat = self.vat_amount or Decimal(0)
        non_tax = self.non_taxable_amount or Decimal(0)
        exempt = self.exempt_amount or Decimal(0)
        tributes = self.tributes_amount or Decimal(0)
        
        expected_total = net + vat + non_tax + exempt + tributes
        
        # Usamos abs() para permitir una diferencia mínima por redondeo de la DB, 
        # aunque con Decimal no debería pasar.
        if abs(self.total_amount - expected_total) > Decimal('0.01'):
            raise ValueError(
                f"Total ({self.total_amount}) no coincide con la suma de componentes ({expected_total}). "
                f"Diferencia: {abs(self.total_amount - expected_total)}"
            )
        
        return self
    
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
    """Schema para parámetros de AFIP (Monedas, Tipos de Comprobante, etc.)"""
    tipo: str
    codigo: str
    descripcion: Optional[str]
    datos_adicionales: Optional[Dict[str, Any]] = None

class FacturaConsultaSchema(BaseModel):
    """Schema para consultar una factura específica en AFIP"""
    tipo_cbte: int = Field(..., description="Tipo de comprobante (1: A, 6: B, etc)")
    punto_vta: int = Field(..., description="Punto de venta")
    numero: int = Field(..., description="Número de comprobante")