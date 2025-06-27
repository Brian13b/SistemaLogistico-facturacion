"""
Servicio de Factura Electrónica de AFIP (WSFE)
"""
from datetime import datetime
from requests import Session
from zeep import Client
from zeep.transports import Transport
import urllib3

from src.config import AFIP_URLS
from src.services.wsaa import WSAAService
from src.core.models import InvoiceRequest, InvoiceResponse
from src.utils.logger import setup_logger
from src.utils.xml_utils import format_wsfe_error

# Suprimir advertencias de certificados SSL no verificados (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logger(__name__)

class WSFEService:
    """Clase para interactuar con el servicio WSFE de AFIP"""
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        """
        Inicializa el servicio WSFE
        
        Args:
            cuit (str): CUIT del contribuyente
            cert_path (str): Ruta al certificado
            key_path (str): Ruta a la clave privada
            testing (bool): Si es True, usa el entorno de homologación
        """
        self.wsaa_service = WSAAService(
            cuit=cuit,
            cert_path=cert_path,
            key_path=key_path,
            testing=testing
        )
        self.testing = testing if testing is not None else self.wsaa_service.authenticator.testing
        self.cuit = cuit or self.wsaa_service.authenticator.cuit
        
        # URL del servicio WSFE según el entorno
        self.wsfe_url = AFIP_URLS["wsfe"]["testing"] if self.testing else AFIP_URLS["wsfe"]["production"]
    
    def _get_client(self):
        """
        Obtiene un cliente para el servicio WSFE
        
        Returns:
            Client: Cliente SOAP para WSFE
        """
        session = Session()
        session.verify = False  # Solo para desarrollo
        transport = Transport(session=session)
        return Client(wsdl=f"{self.wsfe_url}?WSDL", transport=transport)
    
    def _get_auth(self, force_new=False):
        """
        Obtiene un diccionario con los datos de autenticación para WSFE
        
        Args:
            force_new (bool): Si es True, ignora la caché y genera un nuevo token
            
        Returns:
            dict: Diccionario con Token, Sign y Cuit
        """
        return self.wsaa_service.get_auth_dict("wsfe", force_new)
    
    def get_last_voucher(self, sales_point, voucher_type):
        """
        Obtiene el último número de comprobante
        
        Args:
            sales_point (int): Punto de venta
            voucher_type (int): Tipo de comprobante
            
        Returns:
            int: Último número de comprobante
        """
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
        Obtiene los tipos de comprobante disponibles
        
        Returns:
            list: Lista de tipos de comprobante
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando tipos de comprobante")
            result = client.service.FEParamGetTiposCbte(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener tipos de comprobante: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.CbteTipo
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de comprobante: {str(e)}")
            raise
    
    def get_concept_types(self):
        """
        Obtiene los tipos de concepto disponibles
        
        Returns:
            list: Lista de tipos de concepto
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando tipos de concepto")
            result = client.service.FEParamGetTiposConcepto(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener tipos de concepto: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.ConceptoTipo
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de concepto: {str(e)}")
            raise
    
    def get_document_types(self):
        """
        Obtiene los tipos de documento disponibles
        
        Returns:
            list: Lista de tipos de documento
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando tipos de documento")
            result = client.service.FEParamGetTiposDoc(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener tipos de documento: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.DocTipo
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de documento: {str(e)}")
            raise
    
    def get_vat_types(self):
        """
        Obtiene los tipos de IVA disponibles
        
        Returns:
            list: Lista de tipos de IVA
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando tipos de IVA")
            result = client.service.FEParamGetTiposIva(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener tipos de IVA: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.IvaTipo
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de IVA: {str(e)}")
            raise
    
    def get_currency_types(self):
        """
        Obtiene los tipos de moneda disponibles
        
        Returns:
            list: Lista de tipos de moneda
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            logger.debug("Consultando tipos de moneda")
            result = client.service.FEParamGetTiposMonedas(Auth=auth)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al obtener tipos de moneda: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet.Moneda
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de moneda: {str(e)}")
            raise
    
    def create_invoice(self, invoice_request):
        """
        Crea una factura electrónica
        
        Args:
            invoice_request (InvoiceRequest): Datos de la factura
            
        Returns:
            InvoiceResponse: Respuesta de la factura autorizada
        """
        try:
            client = self._get_client()
            auth = self._get_auth()
            
            # Obtener el último número de comprobante
            last_voucher = self.get_last_voucher(
                invoice_request.sales_point,
                invoice_request.voucher_type
            )
            
            # Fecha actual en formato AAAAMMDD
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Preparar los datos de la factura
            invoice_data = {
                'Auth': auth,
                'FeCAEReq': {
                    'FeCabReq': {
                        'CantReg': 1,
                        'PtoVta': invoice_request.sales_point,
                        'CbteTipo': invoice_request.voucher_type
                    },
                    'FeDetReq': {
                        'FECAEDetRequest': [{
                            'Concepto': invoice_request.concept,
                            'DocTipo': invoice_request.doc_type,
                            'DocNro': invoice_request.doc_number,
                            'CbteDesde': last_voucher + 1,
                            'CbteHasta': last_voucher + 1,
                            'CbteFch': current_date,
                            'ImpTotal': invoice_request.total_amount,
                            'ImpTotConc': invoice_request.non_taxable_amount,
                            'ImpNeto': invoice_request.net_amount,
                            'ImpOpEx': invoice_request.exempt_amount,
                            'ImpIVA': invoice_request.vat_amount,
                            'ImpTrib': invoice_request.tributes_amount,
                            'MonId': invoice_request.currency,
                            'MonCotiz': invoice_request.currency_rate,
                        }]
                    }
                }
            }
            
            # Agregar fechas para servicios si es necesario
            if invoice_request.concept in (2, 3):  # 2: Servicios, 3: Productos y Servicios
                invoice_detail = invoice_data['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]
                
                if invoice_request.service_start_date:
                    invoice_detail['FchServDesde'] = invoice_request.service_start_date
                else:
                    invoice_detail['FchServDesde'] = current_date
                    
                if invoice_request.service_end_date:
                    invoice_detail['FchServHasta'] = invoice_request.service_end_date
                else:
                    invoice_detail['FchServHasta'] = current_date
                    
                if invoice_request.payment_due_date:
                    invoice_detail['FchVtoPago'] = invoice_request.payment_due_date
                else:
                    invoice_detail['FchVtoPago'] = current_date
            
            # Agregar IVA si existe
            if invoice_request.vat_details:
                invoice_data['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]['Iva'] = {
                    'AlicIva': [vat_detail.dict() for vat_detail in invoice_request.vat_details]
                }
            
            # Agregar tributos si existen
            if invoice_request.tributes_details:
                invoice_data['FeCAEReq']['FeDetReq']['FECAEDetRequest'][0]['Tributos'] = {
                    'Tributo': [trib_detail.dict() for trib_detail in invoice_request.tributes_details]
                }
            
            logger.info(f"Solicitando CAE para comprobante {invoice_request.voucher_type}, punto de venta {invoice_request.sales_point}")
            result = client.service.FECAESolicitar(**invoice_data)
            
            if hasattr(result, 'Errors') and result.Errors:
                error_msg = format_wsfe_error(result.Errors)
                logger.error(f"Error al crear factura: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            detail_response = result.FeDetResp.FECAEDetResponse[0]
            
            # Crear respuesta
            invoice_response = InvoiceResponse(
                cae=detail_response.CAE,
                cae_expiration=detail_response.CAEFchVto,
                voucher_number=detail_response.CbteDesde,
                voucher_date=current_date,
                status="A" if detail_response.Resultado == "A" else "R",
                observations=[obs.Msg for obs in detail_response.Observaciones.Obs] if hasattr(detail_response, 'Observaciones') and detail_response.Observaciones else None,
                errors=None
            )
            
            logger.info(f"Factura creada con CAE: {invoice_response.cae}, vencimiento: {invoice_response.cae_expiration}")
            return invoice_response
            
        except Exception as e:
            logger.error(f"Error al crear factura: {str(e)}")
            raise
    
    def check_invoice(self, sales_point, voucher_type, voucher_number):
        """
        Consulta una factura existente
        
        Args:
            sales_point (int): Punto de venta
            voucher_type (int): Tipo de comprobante
            voucher_number (int): Número de comprobante
            
        Returns:
            dict: Datos de la factura
        """
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
                logger.error(f"Error al consultar factura: {error_msg}")
                raise Exception(f"Error de AFIP: {error_msg}")
            
            return result.ResultGet
            
        except Exception as e:
            logger.error(f"Error al consultar factura: {str(e)}")
            raise