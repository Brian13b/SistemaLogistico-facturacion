"""
Cliente principal de AFIP para todos los servicios
"""
from src.services.wsaa import WSAAService
from src.services.wsfe import WSFEService
from src.core.models import InvoiceRequest, InvoiceResponse
from src.utils.logger import setup_logger
from src.config import DEFAULT_SALES_POINT

logger = setup_logger(__name__)

class AfipClient:
    """Cliente principal para todos los servicios de AFIP"""
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        """
        Inicializa el cliente de AFIP
        
        Args:
            cuit (str): CUIT del contribuyente
            cert_path (str): Ruta al certificado
            key_path (str): Ruta a la clave privada
            testing (bool): Si es True, usa el entorno de homologación
        """
        # Inicializar servicios
        self.wsaa = WSAAService(cuit, cert_path, key_path, testing)
        self.wsfe = WSFEService(cuit, cert_path, key_path, testing)
        
        # Guardar referencias
        self.cuit = cuit or self.wsaa.authenticator.cuit
        self.testing = testing if testing is not None else self.wsaa.authenticator.testing
    
    def authenticate(self, service="wsfe", force_new=False):
        """
        Autentica con AFIP para un servicio específico
        
        Args:
            service (str): Nombre del servicio (wsfe, padron, etc)
            force_new (bool): Si es True, ignora la caché y genera un nuevo token
            
        Returns:
            dict: Datos de autenticación
        """
        return self.wsaa.get_auth_dict(service, force_new)
    
    def get_last_invoice_number(self, sales_point=None, voucher_type=1):
        """
        Obtiene el último número de factura
        
        Args:
            sales_point (int): Punto de venta
            voucher_type (int): Tipo de comprobante (1: Factura A, 6: Factura B, etc.)
            
        Returns:
            int: Último número de factura
        """
        if sales_point is None:
            sales_point = DEFAULT_SALES_POINT
            
        return self.wsfe.get_last_voucher(sales_point, voucher_type)
    
    def get_invoice_types(self):
        """
        Obtiene los tipos de comprobante disponibles
        
        Returns:
            list: Lista de tipos de comprobante
        """
        return self.wsfe.get_invoice_types()
    
    def get_vat_types(self):
        """
        Obtiene los tipos de IVA disponibles
        
        Returns:
            list: Lista de tipos de IVA
        """
        return self.wsfe.get_vat_types()
    
    def get_concept_types(self):
        """
        Obtiene los tipos de concepto disponibles
        
        Returns:
            list: Lista de tipos de concepto
        """
        return self.wsfe.get_concept_types()
    
    def get_document_types(self):
        """
        Obtiene los tipos de documento disponibles
        
        Returns:
            list: Lista de tipos de documento
        """
        return self.wsfe.get_document_types()
    
    def get_currency_types(self):
        """
        Obtiene los tipos de moneda disponibles
        
        Returns:
            list: Lista de tipos de moneda
        """
        return self.wsfe.get_currency_types()
    
    def create_invoice(self, invoice_data):
        """
        Crea una factura electrónica
        
        Args:
            invoice_data (dict): Datos de la factura
            
        Returns:
            InvoiceResponse: Respuesta de la factura autorizada
        """
        # Convertir a modelo si es un diccionario
        if isinstance(invoice_data, dict):
            invoice_request = InvoiceRequest(**invoice_data)
        else:
            invoice_request = invoice_data
            
        return self.wsfe.create_invoice(invoice_request)
    
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
        return self.wsfe.check_invoice(sales_point, voucher_type, voucher_number)
    
    def create_invoice_a(self, client_cuit, net_amount, vat_rate=21, **kwargs):
        """
        Crea una factura tipo A
        
        Args:
            client_cuit (str): CUIT del cliente
            net_amount (float): Importe neto
            vat_rate (float): Tasa de IVA (21, 10.5, etc.)
            **kwargs: Argumentos adicionales para la factura
            
        Returns:
            InvoiceResponse: Respuesta de la factura autorizada
        """
        # Calcular importes
        vat_amount = net_amount * (vat_rate / 100)
        total_amount = net_amount + vat_amount
        
        # Obtener ID del tipo de IVA
        vat_type_id = 5  # Por defecto 21%
        if vat_rate == 10.5:
            vat_type_id = 4
        elif vat_rate == 27:
            vat_type_id = 6
            
        # Preparar datos de la factura
        invoice_data = {
            'sales_point': kwargs.get('sales_point', DEFAULT_SALES_POINT),
            'voucher_type': 1,  # Factura A
            'concept': kwargs.get('concept', 1),
            'doc_type': 80,  # CUIT
            'doc_number': client_cuit,
            'total_amount': total_amount,
            'net_amount': net_amount,
            'vat_amount': vat_amount,
            'vat_details': [
                {
                    'Id': vat_type_id,
                    'BaseImp': net_amount,
                    'Importe': vat_amount
                }
            ]
        }
        
        # Agregar argumentos adicionales
        for key, value in kwargs.items():
            if key not in invoice_data:
                invoice_data[key] = value
                
        return self.create_invoice(invoice_data)
    
    def create_invoice_b(self, client_doc_type, client_doc_number, total_amount, vat_rate=21, **kwargs):
        """
        Crea una factura tipo B
        
        Args:
            client_doc_type (int): Tipo de documento del cliente
            client_doc_number (str): Número de documento del cliente
            total_amount (float): Importe total (con IVA incluido)
            vat_rate (float): Tasa de IVA (21, 10.5, etc.)
            **kwargs: Argumentos adicionales para la factura
            
        Returns:
            InvoiceResponse: Respuesta de la factura autorizada
        """
        # Calcular importes
        net_amount = total_amount / (1 + (vat_rate / 100))
        vat_amount = total_amount - net_amount
        
        # Obtener ID del tipo de IVA
        vat_type_id = 5  # Por defecto 21%
        if vat_rate == 10.5:
            vat_type_id = 4
        elif vat_rate == 27:
            vat_type_id = 6
            
        # Preparar datos de la factura
        invoice_data = {
            'sales_point': kwargs.get('sales_point', DEFAULT_SALES_POINT),
            'voucher_type': 6,  # Factura B
            'concept': kwargs.get('concept', 1),
            'doc_type': client_doc_type,
            'doc_number': client_doc_number,
            'total_amount': total_amount,
            'net_amount': net_amount,
            'vat_amount': vat_amount,
            'vat_details': [
                {
                    'Id': vat_type_id,
                    'BaseImp': net_amount,
                    'Importe': vat_amount
                }
            ]
        }
        
        # Agregar argumentos adicionales
        for key, value in kwargs.items():
            if key not in invoice_data:
                invoice_data[key] = value
                
        return self.create_invoice(invoice_data)