"""
Utilidades para manejo de XML con soporte UTC y Parsing robusto
"""
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def create_tra_xml(service, ttl=2400):
    """
    Genera el XML para solicitar Ticket de Acceso (TRA).
    Usa UTC para evitar error de 'Firma inválida'.
    """
    try:
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(seconds=ttl)
        
        generation_time = now.strftime("%Y-%m-%dT%H:%M:%S")
        expiration_time = expiration.strftime("%Y-%m-%dT%H:%M:%S")
        unique_id = str(int(now.timestamp()))
        
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{unique_id}</uniqueId>
        <generationTime>{generation_time}</generationTime>
        <expirationTime>{expiration_time}</expirationTime>
    </header>
    <service>{service}</service>
</loginTicketRequest>"""

        return xml.strip()

    except Exception as e:
        logger.error(f"Error al crear XML TRA: {str(e)}")
        raise

def parse_wsaa_response(response):
    """
    Extrae token y sign de la respuesta SOAP.
    Maneja respuestas tanto en formato Objeto (Zeep) como String XML crudo.
    """
    try:
        token = None
        sign = None
        expiration_str = None

        # CASO 1: La respuesta es un String XML (Lo que te está pasando ahora)
        if isinstance(response, str):
            # Parseamos el XML
            root = ET.fromstring(response)
            # Buscamos los tags (usamos .// para buscar en cualquier nivel)
            token = root.find(".//token").text
            sign = root.find(".//sign").text
            expiration_str = root.find(".//expirationTime").text

        # CASO 2: La respuesta es un Objeto Zeep
        elif hasattr(response, 'credentials'):
            token = response.credentials.token
            sign = response.credentials.sign
            expiration_str = response.header.expirationTime
            
        # CASO 3: La respuesta es un Diccionario
        elif isinstance(response, dict):
            token = response['credentials']['token']
            sign = response['credentials']['sign']
            expiration_str = response['header']['expirationTime']

        # Validación final
        if not token or not sign:
            raise ValueError("No se pudieron extraer Token y Sign de la respuesta")

        # Limpiar formato de fecha (a veces trae milisegundos o zona horaria)
        # Ejemplo: 2025-11-21T16:00:00.123-03:00 -> tomamos solo los primeros 19 chars
        if expiration_str and len(expiration_str) > 19:
            expiration_str = expiration_str[:19]
            
        expiration = datetime.strptime(expiration_str, "%Y-%m-%dT%H:%M:%S")

        return {
            "token": token,
            "sign": sign,
            "expiration": expiration
        }
    
    except Exception as e:
        logger.error(f"Error al parsear respuesta WSAA: {str(e)}")
        # Logueamos qué llegó para poder debuguear si falla
        logger.debug(f"Contenido recibido: {response}")
        raise

def format_wsfe_error(errors):
    """Formatea lista de errores de Zeep"""
    if not errors: return "Error desconocido"
    
    msgs = []
    error_list = errors.Err if hasattr(errors, 'Err') else []
    if not isinstance(error_list, list): 
        error_list = [error_list]
    
    for e in error_list:
        code = getattr(e, 'Code', getattr(e, 'code', '?'))
        msg = getattr(e, 'Msg', getattr(e, 'msg', str(e)))
        msgs.append(f"[{code}] {msg}")
        
    return "; ".join(msgs)