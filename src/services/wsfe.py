"""
Servicio de Factura Electrónica de AFIP (WSFE) - Versión Final
Cumple con especificación RG 4291 y ARCA v4.1
"""
from datetime import datetime
from decimal import Decimal
from requests import Session
from zeep import Client
from zeep.transports import Transport
import urllib3

from src.config import Config
from src.services.wsaa import WSAAService
from src.core.models import InvoiceRequest, InvoiceResponse
from src.utils.logger import setup_logger
from src.utils.xml_utils import format_wsfe_error

# Suprimir advertencias de certificados SSL no verificados (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logger(__name__)

class WSFEService:
    """Clase para interactuar con el servicio WSFE de AFIP"""
    class ParametroMock:
        def __init__(self, id_, desc):
            self.Id = id_
            self.Desc = desc
            self.FchDesde = "20200101"
            self.FchHasta = "NULL"

    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        self.wsaa_service = WSAAService(
            cuit=cuit,
            cert_path=cert_path,
            key_path=key_path,
            testing=testing
        )
        self.testing = testing if testing is not None else self.wsaa_service.authenticator.testing
        self.cuit = cuit or self.wsaa_service.authenticator.cuit
        
        # URL del servicio WSFE según el entorno
        self.wsfe_url = Config.AFIP_URLS["wsfe"]["testing"] if self.testing else Config.AFIP_URLS["wsfe"]["production"]
        
        if self.testing:
            logger.warning("⚠️  MODO HOMOLOGACIÓN ACTIVO - No se emitirán facturas reales")
    
    def _get_client(self):
        session = Session()
        session.verify = False  # Solo para desarrollo
        transport = Transport(session=session)
        return Client(wsdl=f"{self.wsfe_url}?WSDL", transport=transport)
    
    def _get_auth(self, force_new=False):
        return self.wsaa_service.get_auth_dict("wsfe", force_new)
    
    def check_server_status(self):
        try:
            client = self._get_client()
            result = client.service.FEDummy()
            return {
                'app_server': result.AppServer,
                'db_server': result.DbServer,
                'auth_server': result.AuthServer
            }
        except Exception as e:
            logger.error(f"Error al verificar estado del servidor: {str(e)}")
            raise
    
    def get_last_voucher(self, sales_point, voucher_type):
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug(f"Consultando último comprobante para PV: {sales_point}, Tipo: {voucher_type}")
            result = client.service.FECompUltimoAutorizado(
                Auth=auth,
                PtoVta=sales_point,
                CbteTipo=voucher_type
            )
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener último comprobante: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            logger.info(f"Último comprobante: {result.CbteNro}")
            return result.CbteNro
            
        except Exception as e:
            logger.error(f"Error al obtener último comprobante: {str(e)}")
            raise
            
    def get_invoice_types(self):
        """
        Obtiene tipos de comprobante (Con fallback para Testing)
        """
        try:
            return self._get_param_data('FEParamGetTiposCbte', 'CbteTipo')
        except Exception as e:
            if self.testing:
                logger.warning(f"Fallo AFIP (Tipos Cbte). Usando datos locales de respaldo. Error: {e}")
                return [
                    self.ParametroMock(1, "Factura A"),
                    self.ParametroMock(2, "Nota de Débito A"),
                    self.ParametroMock(3, "Nota de Crédito A"),
                    self.ParametroMock(6, "Factura B"),
                    self.ParametroMock(7, "Nota de Débito B"),
                    self.ParametroMock(8, "Nota de Crédito B"),
                    self.ParametroMock(11, "Factura C"),
                    self.ParametroMock(12, "Nota de Débito C"),
                    self.ParametroMock(13, "Nota de Crédito C")
                ]
            raise e

    def get_concept_types(self):
        """
        Obtiene tipos de concepto (Con fallback para Testing)
        """
        try:
            return self._get_param_data('FEParamGetTiposConcepto', 'ConceptoTipo')
        except Exception as e:
            if self.testing:
                logger.warning(f"Fallo AFIP (Conceptos). Usando datos locales de respaldo. Error: {e}")
                return [
                    self.ParametroMock(1, "Productos"),
                    self.ParametroMock(2, "Servicios"),
                    self.ParametroMock(3, "Productos y Servicios")
                ]
            raise e

    def get_document_types(self):
        """
        Obtiene tipos de documento (Con fallback para Testing)
        """
        try:
            return self._get_param_data('FEParamGetTiposDoc', 'DocTipo')
        except Exception as e:
            if self.testing:
                logger.warning(f"Fallo AFIP (Tipos Doc). Usando datos locales de respaldo. Error: {e}")
                return [
                    self.ParametroMock(80, "CUIT"),
                    self.ParametroMock(86, "CUIL"),
                    self.ParametroMock(96, "DNI"),
                    self.ParametroMock(99, "Consumidor Final")
                ]
            raise e

    def get_vat_types(self):
        return self._get_param_data('FEParamGetTiposIva', 'IvaTipo')

    def get_currency_types(self):
        return self._get_param_data('FEParamGetTiposMonedas', 'Moneda')

    def get_sales_points(self):
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando puntos de venta")
            result = client.service.FEParamGetPtosVenta(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                
                # Si estamos en testing y AFIP dice "Sin Resultados", devolvemos uno por defecto
                if self.testing and "602" in str(error_msg):
                    logger.warning("AFIP devolvió 602 (Sin Puntos de Venta). Usando PV 1 por defecto para Testing.")
                    
                    class PtoVentaMock:
                        def __init__(self, nro):
                            self.Nro = nro
                            self.Bloqueado = 'N'
                            self.EmisionTipo = 'CAE'
                            self.FchBaja = None
                            
                    return [PtoVentaMock(1)]

                logger.error(f"Error al obtener puntos de venta: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.PtoVenta
            
        except Exception as e:
            logger.error(f"Error al obtener puntos de venta: {str(e)}")
            raise
        
    def _get_param_data(self, method_name, result_key):
        """Método genérico para obtener parámetros"""
        try:
            client = self._get_client()
            auth = self._get_auth()
            method = getattr(client.service, method_name)
            result = method(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return getattr(result.ResultGet, result_key)
        except Exception as e:
            logger.error(f"Error en {method_name}: {str(e)}")
            raise

    def create_invoice(self, invoice_request):
        """
        Crea una factura electrónica adaptada a ARCA v4.1
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            # Obtener último número
            last_voucher = self.get_last_voucher(invoice_request.sales_point, invoice_request.voucher_type)
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Estructura del detalle del comprobante
            detalle = {
                'Concepto': invoice_request.concept,
                'DocTipo': invoice_request.doc_type,
                'DocNro': int(invoice_request.doc_number),
                'CbteDesde': last_voucher + 1,
                'CbteHasta': last_voucher + 1,
                'CbteFch': current_date,
                'ImpTotal': float(invoice_request.total_amount),
                'ImpTotConc': float(invoice_request.non_taxable_amount),
                'ImpNeto': float(invoice_request.net_amount),
                'ImpOpEx': float(invoice_request.exempt_amount),
                'ImpIVA': float(invoice_request.vat_amount),
                'ImpTrib': float(invoice_request.tributes_amount),
                'MonId': invoice_request.currency,
                'MonCotiz': float(invoice_request.currency_rate),
                
                # Nuevos campos ARCA v4.0/4.1
                'CanMisMonExt': invoice_request.can_mis_mon_ext
            }

            # Campo CondicionIVAReceptorId
            if invoice_request.condicion_iva_receptor_id:
                detalle['CondicionIVAReceptorId'] = invoice_request.condicion_iva_receptor_id

            # Manejo de Fechas de Servicio
            if invoice_request.concept in (2, 3):
                detalle['FchServDesde'] = invoice_request.service_start_date or current_date
                detalle['FchServHasta'] = invoice_request.service_end_date or current_date
                detalle['FchVtoPago'] = invoice_request.payment_due_date or current_date

            # Arrays de IVA
            if invoice_request.vat_details:
                detalle['Iva'] = {
                    'AlicIva': [
                        {
                            'Id': v.Id,
                            'BaseImp': float(v.BaseImp),
                            'Importe': float(v.Importe)
                        } for v in invoice_request.vat_details
                    ]
                }
            
            # Arrays de Tributos
            if invoice_request.tributes_details:
                detalle['Tributos'] = {
                    'Tributo': [
                        {
                            'Id': t.Id,
                            'Desc': t.Desc,
                            'BaseImp': float(t.BaseImp),
                            'Alic': float(t.Alic),
                            'Importe': float(t.Importe)
                        } for t in invoice_request.tributes_details
                    ]
                }

            # Armado del Request Completo
            invoice_data_soap = {
                'Auth': auth,
                'FeCAEReq': {
                    'FeCabReq': {
                        'CantReg': 1,
                        'PtoVta': invoice_request.sales_point,
                        'CbteTipo': invoice_request.voucher_type
                    },
                    'FeDetReq': {
                        'FECAEDetRequest': [detalle]
                    }
                }
            }
            
            logger.info(f"Solicitando CAE para comprobante {invoice_request.voucher_type}, PV {invoice_request.sales_point}")
            result = client.service.FECAESolicitar(**invoice_data_soap)
            
            # Verificar errores generales
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al crear factura: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            # Verificar respuesta del detalle
            detail_response = result.FeDetResp.FECAEDetResponse[0]
            
            # Verificar observaciones
            observations = None
            if hasattr(detail_response, 'Observaciones') and detail_response.Observaciones:
                observations = [f"Code {obs.Code}: {obs.Msg}" for obs in detail_response.Observaciones.Obs]
                for obs in observations:
                    logger.warning(f"Observación AFIP: {obs}")
            
            # Verificar rechazo
            if detail_response.Resultado == 'R':
                error_msg = f"Comprobante Rechazado. {observations}"
                raise Exception(error_msg)

            # Crear respuesta exitosa
            invoice_response = InvoiceResponse(
                cae=detail_response.CAE,
                cae_expiration=detail_response.CAEFchVto,
                voucher_number=detail_response.CbteDesde,
                voucher_date=current_date,
                status="A",
                observations=observations,
                errors=None
            )
            
            logger.info(f"✅ Factura creada con CAE: {invoice_response.cae}")
            # CORRECCIÓN: Devolvemos el objeto directamente
            return invoice_response
            
        except Exception as e:
            logger.error(f"Error en create_invoice: {str(e)}")
            raise

    def check_invoice(self, sales_point, voucher_type, voucher_number):
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug(f"Consultando comprobante: PV {sales_point}, Tipo {voucher_type}, Número {voucher_number}")
            result = client.service.FECompConsultar(
                Auth=auth,
                FeCompConsReq={
                    'PtoVta': sales_point,
                    'CbteTipo': voucher_type,
                    'CbteNro': voucher_number
                }
            )
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet
            
        except Exception as e:
            logger.error(f"Error al consultar factura: {str(e)}")
            raise

    def get_condicion_iva_receptor(self):
        """
        Nuevo método v4.0: Recuperar condiciones de IVA receptor
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            return client.service.FEParamGetCondicionIvaReceptor(Auth=auth)
        except Exception as e:
            logger.error(f"Error obteniendo condiciones IVA: {e}")
            raise