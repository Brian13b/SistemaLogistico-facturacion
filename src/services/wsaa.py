"""
Servicio de Autenticación y Autorización de AFIP (WSAA)
"""
from src.core.auth import AfipAuthenticator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class WSAAService:
    """Clase para interactuar con el servicio WSAA de AFIP"""
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None):
        """
        Inicializa el servicio WSAA
        
        Args:
            cuit (str): CUIT del contribuyente
            cert_path (str): Ruta al certificado
            key_path (str): Ruta a la clave privada
            testing (bool): Si es True, usa el entorno de homologación
        """
        self.authenticator = AfipAuthenticator(
            cuit=cuit,
            cert_path=cert_path,
            key_path=key_path,
            testing=testing
        )
    
    def get_auth(self, service="wsfe", force_new=False):
        """
        Obtiene los datos de autenticación para un servicio
        
        Args:
            service (str): Nombre del servicio (wsfe, padron, etc)
            force_new (bool): Si es True, ignora la caché y genera un nuevo token
            
        Returns:
            AfipAuth: Datos de autenticación
        """
        return self.authenticator.authenticate(service, force_new)
    
    def get_auth_dict(self, service="wsfe", force_new=False):
        """
        Obtiene un diccionario con los datos de autenticación para un servicio
        
        Args:
            service (str): Nombre del servicio (wsfe, padron, etc)
            force_new (bool): Si es True, ignora la caché y genera un nuevo token
            
        Returns:
            dict: Diccionario con Token, Sign y Cuit
        """
        auth = self.get_auth(service, force_new)
        return {
            'Token': auth.token,
            'Sign': auth.sign,
            'Cuit': auth.cuit
        }