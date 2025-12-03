import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

# Rutas de archivos
BASE_DIR = Path(__file__).resolve().parent.parent
CERTS_DIR = BASE_DIR / "certs"

class Config:
    # Rutas de archivos
    BASE_DIR = BASE_DIR
    CERTS_DIR = CERTS_DIR
    PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "/tmp")

    # Configuración AFIP
    AFIP_CONFIG = {
        "cuit": os.getenv("AFIP_CUIT"),
        "cert_path": os.getenv("AFIP_CERT_PATH", str(CERTS_DIR / "certificado.crt")),
        "key_path": os.getenv("AFIP_KEY_PATH", str(CERTS_DIR / "clave_privada.key")),
        "testing": os.getenv("AFIP_TESTING", "True").lower() in ("true", "1", "t"),
    }

    # URLs de los servicios
    AFIP_URLS = {
        "wsaa": {
            "testing": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
            "production": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
        },
        "wsfe": {
            "testing": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
            "production": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
        }
    }

    # Configuración de logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "afip.log"))

    # Tiempo de expiración del token de autenticación (en segundos)
    TOKEN_TTL = int(os.getenv("TOKEN_TTL", "2400"))  # 40 minutos

    # Configuración para facturación
    DEFAULT_SALES_POINT = int(os.getenv("DEFAULT_SALES_POINT", "1"))

    COMPANY_NAME = os.getenv("COMPANY_NAME", "Mi Empresa S.A.")
    COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "Domicilio Desconocido")
