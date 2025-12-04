import os
import pickle
import ctypes
from datetime import datetime
from requests import Session
from zeep import Client
from zeep.transports import Transport
from urllib3.exceptions import InsecureRequestWarning
import requests

from src.config import Config
from src.utils.logger import setup_logger
from src.utils.cert_utils import read_cert_and_key, sign_data
from src.utils.xml_utils import create_tra_xml, parse_wsaa_response
from src.core.models import AfipAuth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = setup_logger(__name__)

AFIP_CONFIG = Config.AFIP_CONFIG
AFIP_URLS = Config.AFIP_URLS
TOKEN_TTL = Config.TOKEN_TTL
BASE_DIR = Config.BASE_DIR

class AfipAuthenticator:
    
    def __init__(self, cuit=None, cert_path=None, key_path=None, testing=None, cache_dir=None):
        self.cuit = cuit or AFIP_CONFIG["cuit"]
        self.cert_path = cert_path or AFIP_CONFIG["cert_path"]
        self.key_path = key_path or AFIP_CONFIG["key_path"]
        self.testing = testing if testing is not None else AFIP_CONFIG["testing"]
        self.cache_dir = cache_dir or os.path.join(BASE_DIR, "cache")
        
        # URL del servicio WSAA según el entorno
        self.wsaa_url = AFIP_URLS["wsaa"]["testing"] if self.testing else AFIP_URLS["wsaa"]["production"]
        
        # Crear directorio de caché si no existe
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_path(self, service):

        # Obtiene la ruta del archivo de caché para un servicio
        environment = "testing" if self.testing else "production"
        return os.path.join(self.cache_dir, f"{service}_{environment}_{self.cuit}.pkl")
    
    def _load_auth_from_cache(self, service):
        cache_path = self._get_cache_path(service)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                auth = pickle.load(f)
            
            # Verificar si expiró
            if auth.is_valid:
                logger.info(f"Autenticación cargada desde caché para {service}")
                return auth
            else:
                logger.info(f"Autenticación en caché expirada para {service}")
                return None
                
        except Exception as e:
            logger.error(f"Error al cargar autenticación desde caché: {str(e)}")
            return None
    
    def _save_auth_to_cache(self, service, auth):
        cache_path = self._get_cache_path(service)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(auth, f)
            logger.info(f"Autenticación guardada en caché para {service}")
        except Exception as e:
            logger.error(f"Error al guardar autenticación en caché: {str(e)}")
    
    def authenticate(self, service="wsfe", force_new=False):
        # Verificar si hay una autenticación válida en caché
        if not force_new:
            cached_auth = self._load_auth_from_cache(service)
            if cached_auth:
                return cached_auth
        
        try:
            logger.info(f"Iniciando autenticación para servicio {service}")
            
            # Leer certificado y clave
            cert_content, key_content = read_cert_and_key(self.cert_path, self.key_path)
            
            # Carga la configuración de OpenSSL que habilita proveedores legacy
            openssl_conf_path = os.path.join(BASE_DIR, 'src', 'config', 'openssl.cnf')
            libcrypto_found = False
            for lib_name in ("libcrypto.so.3", "libcrypto.so.1.1"):
                try:
                    libcrypto = ctypes.CDLL(lib_name)
                    libcrypto.OPENSSL_config(openssl_conf_path.encode('utf-8'))
                    libcrypto_found = True
                    break
                except OSError:
                    logger.debug(f"No se encontró la librería '{lib_name}'. Intentando con la siguiente.")
                    continue
            
            # Crear TRA
            tra_xml = create_tra_xml(service, TOKEN_TTL)
            
            # Firmar TRA
            signed_tra = sign_data(tra_xml, cert_content, key_content, detached=False)
            
            # Crear cliente SOAP para WSAA
            session = Session()
            session.verify = False
            transport = Transport(session=session, timeout=30) 
            client = Client(wsdl=f"{self.wsaa_url}?WSDL", transport=transport)
            
            # Enviar TRA y obtener respuesta
            logger.debug("Enviando solicitud de autenticación a AFIP")
            wsaa_response = client.service.loginCms(signed_tra)
            
            # Parsear respuesta
            auth_data = parse_wsaa_response(wsaa_response)
            
            # Crear objeto de autenticación
            auth = AfipAuth(
                token=auth_data['token'],
                sign=auth_data['sign'],
                cuit=self.cuit,
                expiration=auth_data['expiration']
            )
            
            logger.info(f"Autenticación exitosa")
            
            # Guardar en caché
            self._save_auth_to_cache(service, auth)
            
            return auth
        
        except requests.exceptions.ConnectTimeout:
            logger.error("Error de red: Timeout al intentar conectar con el servidor de AFIP (WSAA). Verifica la conectividad de red del contenedor.")
            raise Exception("Error de red: No se pudo conectar con AFIP (WSAA).")
        except requests.exceptions.ReadTimeout:
            logger.error("Error de red: Timeout de lectura esperando respuesta de AFIP (WSAA). El servidor podría estar lento.")
            raise Exception("Error de red: AFIP (WSAA) no respondió a tiempo.")
        except Exception as e:
            if "Firma inválida" in str(e):
                 logger.error(f"Error en autenticación")
                 raise
            else:
                logger.error(f"Error inesperado durante la autenticación")
                raise Exception(f"Firma inválida o algoritmo no soportado")