from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime
from fastapi.responses import FileResponse
from src.utils.pdf_generator import FacturaPDF 

from src.database.database import get_db
from src.database.models import Factura
from src.schemas.factura import (
    FacturaRequestSchema,
    FacturaResponseSchema,
    FacturaListSchema,
    FacturaConsultaSchema,
    ParametroAFIPSchema
)
from src.core.client import AfipClient
from src.core.models import InvoiceRequest, VatDetail, TributeDetail
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/facturas", tags=["facturas"])

def get_afip_client():
    """Obtiene una instancia del cliente AFIP"""
    afip_config = Config.AFIP_CONFIG
    return AfipClient(
        cuit=afip_config["cuit"],
        cert_path=afip_config["cert_path"],
        key_path=afip_config["key_path"],
        testing=afip_config["testing"]
    )


@router.post("/emitir", response_model=FacturaResponseSchema, status_code=status.HTTP_201_CREATED)
async def emitir_factura(factura_data: FacturaRequestSchema, db: Session = Depends(get_db), afip_client: AfipClient = Depends(get_afip_client)):
    try:
        # Convertir los detalles de IVA y tributos al formato del modelo
        vat_details = None
        if factura_data.vat_details:
            vat_details = [
                VatDetail(
                    Id=vat.id,
                    BaseImp=vat.base_imp,
                    Importe=vat.importe
                )
                for vat in factura_data.vat_details
            ]
        
        tributes_details = None
        if factura_data.tributes_details:
            tributes_details = [
                TributeDetail(
                    Id=trib.id,
                    Desc=trib.desc,
                    BaseImp=trib.base_imp,
                    Alic=trib.alic,
                    Importe=trib.importe
                )
                for trib in factura_data.tributes_details
            ]
        
        # Crear request para AFIP
        invoice_request = InvoiceRequest(
            sales_point=factura_data.sales_point,
            voucher_type=factura_data.voucher_type,
            concept=factura_data.concept,
            doc_type=factura_data.doc_type,
            doc_number=factura_data.doc_number,
            total_amount=factura_data.total_amount,
            net_amount=factura_data.net_amount,
            vat_amount=factura_data.vat_amount,
            non_taxable_amount=factura_data.non_taxable_amount,
            exempt_amount=factura_data.exempt_amount,
            tributes_amount=factura_data.tributes_amount,
            service_start_date=factura_data.service_start_date,
            service_end_date=factura_data.service_end_date,
            payment_due_date=factura_data.payment_due_date,
            currency=factura_data.currency,
            currency_rate=factura_data.currency_rate,
            vat_details=vat_details,
            tributes_details=tributes_details,
            condicion_iva_receptor_id=factura_data.condicion_iva_receptor_id,
            can_mis_mon_ext=factura_data.can_mis_mon_ext
        )
        
        # Crear factura en AFIP
        invoice_response = afip_client.create_invoice(invoice_request)
        
        if not invoice_response.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La factura fue rechazada por AFIP. Observaciones: {invoice_response.observations}"
            )
        
        # Preparar datos para JSON
        detalles_iva_json = None
        if factura_data.vat_details:
            # Convertimos cada campo Decimal a float explícitamente
            detalles_iva_json = json.dumps([
                {
                    'id': v.id,
                    'base_imp': float(v.base_imp), 
                    'importe': float(v.importe)
                } 
                for v in factura_data.vat_details
            ])

        detalles_tributos_json = None
        if factura_data.tributes_details:
            detalles_tributos_json = json.dumps([
                {
                    'id': t.id,
                    'desc': t.desc,
                    'base_imp': float(t.base_imp),
                    'alic': float(t.alic),
                    'importe': float(t.importe)
                }
                for t in factura_data.tributes_details
            ])
        
        # Guardar factura en la base de datos
        factura_db = Factura(
            tipo_cbte=factura_data.voucher_type,
            punto_vta=factura_data.sales_point,
            numero=invoice_response.voucher_number,
            fecha_cbte=invoice_response.voucher_date,
            concepto=factura_data.concept,
            tipo_doc=factura_data.doc_type,
            nro_doc=factura_data.doc_number,
            cantidad=factura_data.cantidad,
            unidad_medida=factura_data.unidad_medida,
            precio_unitario=factura_data.precio_unitario,
            alicuota_iva=factura_data.alicuota_iva,
            imp_total=factura_data.total_amount,
            imp_neto=factura_data.net_amount,
            imp_iva=factura_data.vat_amount,
            imp_trib=factura_data.tributes_amount,
            imp_op_ex=factura_data.exempt_amount,
            imp_tot_conc=factura_data.non_taxable_amount,
            cae=invoice_response.cae,
            fecha_vto_cae=invoice_response.cae_expiration,
            estado=invoice_response.status,

            observaciones=json.dumps(invoice_response.observations) if invoice_response.observations else None,
            viaje_id=factura_data.viaje_id,

            detalles_iva=detalles_iva_json,
            detalles_tributos=detalles_tributos_json,
            moneda=factura_data.currency,
            moneda_cotiz=factura_data.currency_rate,

            condicion_iva_receptor_id=factura_data.condicion_iva_receptor_id,
            can_mis_mon_ext=factura_data.can_mis_mon_ext,
            descripcion=factura_data.description,
            pdf_generado=False
        )
        
        db.add(factura_db)
        db.commit()
        db.refresh(factura_db)
        
        logger.info(f"Factura {factura_db.numero} emitida exitosamente con CAE: {factura_db.cae}")
        
        return factura_db
        
    except Exception as e:
        logger.error(f"Error al emitir factura: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al emitir factura: {str(e)}"
        )


@router.get("/", response_model=List[FacturaListSchema])
async def listar_facturas(skip: int = 0, limit: int = 50, viaje_id: Optional[int] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(Factura)
        
        if viaje_id:
            query = query.filter(Factura.viaje_id == viaje_id)
        
        facturas = query.order_by(Factura.fecha_creacion.desc()).offset(skip).limit(limit).all()
        return facturas
        
    except Exception as e:
        logger.error(f"Error al listar facturas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar facturas: {str(e)}"
        )


@router.get("/{factura_id}", response_model=FacturaResponseSchema)
async def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    try:
        factura = db.query(Factura).filter(Factura.id == factura_id).first()
        
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        return factura
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener factura: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener factura: {str(e)}"
        )


@router.post("/consultar", response_model=dict)
async def consultar_factura_afip(consulta: FacturaConsultaSchema, afip_client: AfipClient = Depends(get_afip_client)):
    try:
        result = afip_client.check_invoice(
            consulta.punto_vta,
            consulta.tipo_cbte,
            consulta.numero
        )
        
        return {
            "success": True,
            "data": {
                "tipo_cbte": result.CbteTipo,
                "punto_vta": result.PtoVta,
                "numero": result.CbteNro,
                "fecha_cbte": result.CbteFch,
                "cae": result.CAE,
                "fecha_vto_cae": result.FchVtoCAE,
                "resultado": result.Resultado,
                "imp_total": result.ImpTotal,
                "imp_neto": result.ImpNeto,
                "imp_iva": result.ImpIVA,
            }
        }
        
    except Exception as e:
        logger.error(f"Error al consultar factura en AFIP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar factura: {str(e)}"
        )


@router.get("/parametros/tipos-comprobante", response_model=List[ParametroAFIPSchema])
async def obtener_tipos_comprobante(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        tipos = afip_client.get_invoice_types()
        return [
            ParametroAFIPSchema(
                tipo="tipo_comprobante",
                codigo=str(tipo.Id),
                descripcion=tipo.Desc,
                datos_adicionales={"fecha_desde": str(tipo.FchDesde) if hasattr(tipo, 'FchDesde') else None}
            )
            for tipo in tipos
        ]
        
    except Exception as e:
        logger.error(f"Error al obtener tipos de comprobante: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tipos de comprobante: {str(e)}"
        )


@router.get("/parametros/puntos-venta", response_model=List[ParametroAFIPSchema])
async def obtener_puntos_venta(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        puntos = afip_client.wsfe.get_sales_points()
        return [
            ParametroAFIPSchema(
                tipo="punto_venta",
                codigo=str(punto.Nro),
                descripcion=f"Punto de venta {punto.Nro}",
                datos_adicionales={
                    "bloqueado": punto.Bloqueado if hasattr(punto, 'Bloqueado') else False
                }
            )
            for punto in puntos
        ]
        
    except Exception as e:
        logger.error(f"Error al obtener puntos de venta: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener puntos de venta: {str(e)}"
        )


@router.get("/parametros/tipos-documento", response_model=List[ParametroAFIPSchema])
async def obtener_tipos_documento(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        tipos = afip_client.get_document_types()
        return [
            ParametroAFIPSchema(
                tipo="tipo_documento",
                codigo=str(tipo.Id),
                descripcion=tipo.Desc,
                datos_adicionales={"fecha_desde": str(tipo.FchDesde) if hasattr(tipo, 'FchDesde') else None}
            )
            for tipo in tipos
        ]
        
    except Exception as e:
        logger.error(f"Error al obtener tipos de documento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tipos de documento: {str(e)}"
        )


@router.get("/parametros/tipos-iva", response_model=List[ParametroAFIPSchema])
async def obtener_tipos_iva(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        tipos = afip_client.get_vat_types()
        return [
            ParametroAFIPSchema(
                tipo="tipo_iva",
                codigo=str(tipo.Id),
                descripcion=tipo.Desc,
                datos_adicionales={
                    "alicuota": float(tipo.Alic) if hasattr(tipo, 'Alic') else None,
                    "fecha_desde": str(tipo.FchDesde) if hasattr(tipo, 'FchDesde') else None
                }
            )
            for tipo in tipos
        ]
        
    except Exception as e:
        logger.error(f"Error al obtener tipos de IVA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tipos de IVA: {str(e)}"
        )


@router.get("/parametros/tipos-concepto", response_model=List[ParametroAFIPSchema])
async def obtener_tipos_concepto(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        tipos = afip_client.get_concept_types()
        return [
            ParametroAFIPSchema(
                tipo="tipo_concepto",
                codigo=str(tipo.Id),
                descripcion=tipo.Desc,
                datos_adicionales={"fecha_desde": str(tipo.FchDesde) if hasattr(tipo, 'FchDesde') else None}
            )
            for tipo in tipos
        ]
        
    except Exception as e:
        logger.error(f"Error al obtener tipos de concepto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tipos de concepto: {str(e)}"
        )


@router.get("/estado/servidores", response_model=dict)
async def estado_servidores(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        estado = afip_client.wsfe.check_server_status()
        return {
            "success": True,
            "wsfe": {
                "app_server": estado.get('app_server', 'Desconocido'),
                "db_server": estado.get('db_server', 'Desconocido'),
                "auth_server": estado.get('auth_server', 'Desconocido')
            },
            "modo": "homologación" if afip_client.testing else "producción"
        }
        
    except Exception as e:
        logger.error(f"Error al verificar estado de servidores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar estado: {str(e)}"
        )

@router.get("/parametros/cotizacion/{moneda_id}", response_model=dict)
async def obtener_cotizacion(moneda_id: str, afip_client: AfipClient = Depends(get_afip_client)):
    try:
        # Accedemos directamente al servicio WSFE del cliente
        client = afip_client.wsfe._get_client()
        auth = afip_client.wsfe._get_auth()
        
        result = client.service.FEParamGetCotizacion(Auth=auth, MonId=moneda_id)
        
        if hasattr(result, 'Errors') and result.Errors:
            raise Exception(f"Error AFIP: {result.Errors}")
            
        return {
            "moneda": result.ResultGet.MonId,
            "importe": result.ResultGet.MonCotiz,
            "fecha": str(result.ResultGet.FchCotiz)
        }
    except Exception as e:
        logger.error(f"Error al obtener cotización: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ultimo-comprobante/{punto_venta}/{tipo_cbte}", response_model=dict)
async def obtener_ultimo_comprobante(punto_venta: int, tipo_cbte: int, afip_client: AfipClient = Depends(get_afip_client)):
    try:
        ultimo = afip_client.get_last_invoice_number(punto_venta, tipo_cbte)
        return {
            "punto_venta": punto_venta,
            "tipo_comprobante": tipo_cbte,
            "ultimo_numero": ultimo
        }
    except Exception as e:
        logger.error(f"Error consultando último comprobante: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/parametros/condiciones-iva-receptor", response_model=List[ParametroAFIPSchema])
async def obtener_condiciones_iva_receptor(afip_client: AfipClient = Depends(get_afip_client)):
    try:
        condiciones = afip_client.wsfe.get_condicion_iva_receptor()
        
        return [
            ParametroAFIPSchema(
                tipo="condicion_iva_receptor",
                codigo=str(cond.Id),
                descripcion=cond.Desc,
                datos_adicionales={"clase_cmp": cond.Cmp_Clase}
            )
            for cond in condiciones.ResultGet.CondicionIvaReceptor
        ]
    except Exception as e:
        logger.error(f"Error obteniendo condiciones IVA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{factura_id}/pdf")
async def descargar_pdf(factura_id: int, db: Session = Depends(get_db)):
    try:
        factura = db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        pdf_config = {
            'pdf_output_dir': '/tmp',
            'razon_social': Config.COMPANY_NAME,
            'cuit': Config.AFIP_CONFIG['cuit'],
            'domicilio': Config.COMPANY_ADDRESS
        }
        
        # Generar PDF
        pdf_gen = FacturaPDF(pdf_config)
        
        factura_dict = {c.name: getattr(factura, c.name) for c in factura.__table__.columns}
        
        path = pdf_gen.generar_pdf(factura_dict)
        
        return FileResponse(
            path, 
            media_type='application/pdf', 
            filename=f"Factura_{factura.punto_vta}-{factura.numero}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error generando PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")