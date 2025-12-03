from src.services.wsaa import WSAAService
from src.services.wsfe import WSFEService
from src.core.models import InvoiceRequest, InvoiceResponse
from src.utils.logger import setup_logger
from src.config import Config

logger = setup_logger(__name__)

class AfipClient:
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        # Inicializar servicios
        self.wsaa = WSAAService(cuit, cert_path, key_path, testing)
        self.wsfe = WSFEService(cuit, cert_path, key_path, testing)
        
        # Guardar referencias
        self.cuit = cuit or self.wsaa.authenticator.cuit
        self.testing = testing if testing is not None else self.wsaa.authenticator.testing
    
    def authenticate(self, service="wsfe", force_new=False):
        # Autenticar servicios
        return self.wsaa.get_auth_dict(service, force_new)
    
    def get_last_invoice_number(self, sales_point=None, voucher_type=1):
        # Obtiene ultimo numero comprobante
        if sales_point is None:
            sales_point = Config.DEFAULT_SALES_POINT
            
        return self.wsfe.get_last_voucher(sales_point, voucher_type)
    
    def get_invoice_types(self):
        # Tipos de comprobantes
        return self.wsfe.get_invoice_types()
    
    def get_vat_types(self):
        # Tipos de IVA
        return self.wsfe.get_vat_types()
    
    def get_concept_types(self):
        # Obtiene tipo de conceptos 
        return self.wsfe.get_concept_types()
    
    def get_document_types(self):
        # Tipos de documentos
        return self.wsfe.get_document_types()
    
    def get_currency_types(self):
        # Tipos de monedas
        return self.wsfe.get_currency_types()
    
    def create_invoice(self, invoice_data):
        # Convertir a modelo si es un diccionario
        if isinstance(invoice_data, dict):
            invoice_request = InvoiceRequest(**invoice_data)
        else:
            invoice_request = invoice_data
        
        # Crear factura
        return self.wsfe.create_invoice(invoice_request)
    
    def check_invoice(self, sales_point, voucher_type, voucher_number):
        # Consultar factura
        return self.wsfe.check_invoice(sales_point, voucher_type, voucher_number)
    
    def create_invoice_a(self, client_cuit, net_amount, vat_rate=21, **kwargs):
        # Mapeo de tasas de IVA a sus IDs correspondientes en AFIP
        VAT_RATE_TO_ID = {
            21: 5,
            10.5: 4,
            27: 6,
        }

        # Calcular importes
        vat_amount = net_amount * (vat_rate / 100)
        total_amount = net_amount + vat_amount
        
        vat_type_id = VAT_RATE_TO_ID.get(vat_rate)
        if vat_type_id is None:
            raise ValueError(f"Tasa de IVA no soportada: {vat_rate}")
            
        # Preparar datos de la factura
        invoice_data = {
            'sales_point': kwargs.get('sales_point', Config.DEFAULT_SALES_POINT),
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
        # Mapeo de tasas de IVA a sus IDs correspondientes en AFIP
        VAT_RATE_TO_ID = {
            21: 5,
            10.5: 4,
            27: 6,
        }
        
        # Calcular importes
        net_amount = total_amount / (1 + (vat_rate / 100))
        vat_amount = total_amount - net_amount
        
        vat_type_id = VAT_RATE_TO_ID.get(vat_rate)
        if vat_type_id is None:
            raise ValueError(f"Tasa de IVA no soportada: {vat_rate}")
            
        # Preparar datos de la factura
        invoice_data = {
            'sales_point': kwargs.get('sales_point', Config.DEFAULT_SALES_POINT),
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