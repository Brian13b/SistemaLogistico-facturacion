"""
Utilidades para manejo de XML con ajuste temporal para AFIP
"""
from datetime import datetime, timedelta
import zoneinfo # Estándar en Python 3.9+
from src.utils.logger import setup_logger
import xml.etree.ElementTree as ET

logger = setup_logger(__name__)

def create_tra_xml(service, ttl=2400):
    """
    Genera el XML para solicitar Ticket de Acceso (TRA).
    Aplica un retraso de 10 minutos para evitar error 'generationTime in the future'.
    """
    try:
        # 1. Obtener hora Argentina
        try:
            tz_arg = zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")
            now_real = datetime.now(tz_arg)
        except Exception:
            # Fallback manual a UTC-3 si no encuentra la zona
            timezone_offset = -3.0 
            tzinfo = datetime.timezone(datetime.timedelta(hours=timezone_offset))
            now_real = datetime.now(tzinfo)

        # 2. EL FIX MÁGICO: Restar 10 minutos
        # Esto garantiza que AFIP nunca vea el ticket como "del futuro" 
        # por diferencias de reloj entre servidores.
        now = now_real - timedelta(minutes=10)
        expiration = now + timedelta(seconds=ttl)
        
        # Formato requerido por AFIP
        generation_time = now.strftime("%Y-%m-%dT%H:%M:%S")
        expiration_time = expiration.strftime("%Y-%m-%dT%H:%M:%S")
        
        # ID único
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

        # CASO 1: La respuesta es un String XML
        if isinstance(response, str):
            root = ET.fromstring(response)
            # Buscamos los tags recursivamente
            token_node = root.find(".//token")
            sign_node = root.find(".//sign")
            time_node = root.find(".//expirationTime")
            
            if token_node is not None: token = token_node.text
            if sign_node is not None: sign = sign_node.text
            if time_node is not None: expiration_str = time_node.text

        # CASO 2: La respuesta es un Objeto Zeep
        elif hasattr(response, 'credentials'):
            token = response.credentials.token
            sign = response.credentials.sign
            expiration_str = response.header.expirationTime
            
        # CASO 3: La respuesta es un Diccionario
        elif isinstance(response, dict):
            token = response.get('credentials', {}).get('token')
            sign = response.get('credentials', {}).get('sign')
            expiration_str = response.get('header', {}).get('expirationTime')

        if not token or not sign:
            raise ValueError(f"No se pudo extraer Token/Sign. Respuesta recibida tipo {type(response)}")

        # Limpiar formato de fecha
        if expiration_str and len(str(expiration_str)) > 19:
            expiration_str = str(expiration_str)[:19]
            
        # Si viene como objeto datetime (caso Zeep a veces), lo usamos directo
        if isinstance(expiration_str, datetime):
            expiration = expiration_str
        else:
            expiration = datetime.strptime(expiration_str, "%Y-%m-%dT%H:%M:%S")

        return {
            "token": token,
            "sign": sign,
            "expiration": expiration
        }
    
    except Exception as e:
        logger.error(f"Error al parsear respuesta WSAA: {str(e)}")
        logger.debug(f"Contenido recibido para debug: {response}")
        raise

def format_wsfe_error(errors):
    """Formatea lista de errores de Zeep"""
    if not errors: return "Error desconocido"
    
    msgs = []
    # Zeep a veces devuelve una lista y a veces un solo objeto
    error_list = errors.Err if hasattr(errors, 'Err') else []
    if not isinstance(error_list, list): 
        error_list = [error_list]
    
    for e in error_list:
        code = getattr(e, 'Code', getattr(e, 'code', '?'))
        msg = getattr(e, 'Msg', getattr(e, 'msg', str(e)))
        msgs.append(f"[{code}] {msg}")
        
    return "; ".join(msgs)