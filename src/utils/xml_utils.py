from datetime import datetime, timedelta, timezone 
from src.utils.logger import setup_logger 

logger = setup_logger(__name__)

def create_tra_xml(service, ttl=2400):
    """
    Genera el XML para solicitar Ticket de Acceso (TRA)
    Usa hora UTC explícita para evitar errores de 'Firma inválida' por desfase de reloj.
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
    """Extrae token y sign de la respuesta SOAP"""
    return {
        "token": response.credentials.token,
        "sign": response.credentials.sign,
        "expiration": response.header.expirationTime
    }

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