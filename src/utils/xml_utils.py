import datetime
import pytz # Recomendado agregar pytz a requirements.txt para seguridad horaria

def create_tra_xml(service, ttl=2400):
    """Genera el XML para solicitar Ticket de Acceso"""
    # AFIP usa hora Buenos Aires o UTC. Usamos Buenos Aires para seguridad.
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.datetime.now(tz)
    expiration = now + datetime.timedelta(seconds=ttl)
    
    # Formato estricto de AFIP: YYYY-MM-DDThh:mm:ss
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
    # Zeep devuelve una lista de objetos Err
    error_list = errors.Err if hasattr(errors, 'Err') else []
    if not isinstance(error_list, list): error_list = [error_list]
    
    for e in error_list:
        msgs.append(f"[{e.Code}] {e.Msg}")
    return "; ".join(msgs)