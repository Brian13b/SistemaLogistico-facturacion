from datetime import datetime, timedelta, timezone 
import zoneinfo
from src.utils.logger import setup_logger 

logger = setup_logger(__name__)

def create_tra_xml(service, ttl=2400):
    """
    Genera el XML para solicitar Ticket de Acceso (TRA)
    Usa explícitamente la hora de Argentina para evitar rechazo por 'Firma inválida'.
    """
    try:
        # Definir zona horaria de Argentina
        # Render suele tener la base de datos de zonas horarias, si fallara, usaremos un offset manual
        try:
            tz_arg = zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")
            now = datetime.now(tz_arg)
        except Exception:
            # Fallback manual a UTC-3 si no encuentra la zona
            timezone_offset = -3.0 
            tzinfo = datetime.timezone(datetime.timedelta(hours=timezone_offset))
            now = datetime.now(tzinfo)

        expiration = now + timedelta(seconds=ttl)
        
        # Formato requerido por AFIP: YYYY-MM-DDThh:mm:ss
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
    """Extrae token y sign de la respuesta SOAP"""
    # Nota: response suele ser un objeto Zeep, no un XML crudo
    try:
        return {
            "token": response.credentials.token,
            "sign": response.credentials.sign,
            "expiration": response.header.expirationTime
        }
    except Exception:
        # Fallback si la estructura es diferente (a veces pasa con zeep raw)
        # Intentamos acceder como diccionario si falla como objeto
        return {
            "token": response['credentials']['token'],
            "sign": response['credentials']['sign'],
            "expiration": response['header']['expirationTime']
        }

def format_wsfe_error(errors):
    """Formatea lista de errores de Zeep"""
    if not errors: return "Error desconocido"
    
    msgs = []
    # Manejo robusto de errores de Zeep (lista o item único)
    error_list = errors.Err if hasattr(errors, 'Err') else []
    if not isinstance(error_list, list): 
        error_list = [error_list]
    
    for e in error_list:
        code = getattr(e, 'Code', getattr(e, 'code', '?'))
        msg = getattr(e, 'Msg', getattr(e, 'msg', str(e)))
        msgs.append(f"[{code}] {msg}")
        
    return "; ".join(msgs)