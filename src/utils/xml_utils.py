"""
Utilidades para manejo de XML
"""
import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def create_tra_xml(service, ttl=2400):
    """
    Crea un XML para el Ticket de Requerimiento de Acceso (TRA)
    
    Args:
        service (str): Servicio a acceder (wsfe, padron, etc)
        ttl (int): Tiempo de vida del ticket en segundos
        
    Returns:
        str: XML del TRA
    """
    try:
        # Crear fechas
        now = datetime.datetime.now()
        expiration = now + datetime.timedelta(seconds=ttl)
        
        # Crear XML
        tra_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
        <loginTicketRequest version="1.0">
            <header>
                <uniqueId>{str(int(datetime.datetime.timestamp(now)))}</uniqueId>
                <generationTime>{now.strftime("%Y-%m-%dT%H:%M:%S")}</generationTime>
                <expirationTime>{expiration.strftime("%Y-%m-%dT%H:%M:%S")}</expirationTime>
            </header>
            <service>{service}</service>
        </loginTicketRequest>"""
        
        return tra_xml
    
    except Exception as e:
        logger.error(f"Error al crear XML TRA: {str(e)}")
        raise

def parse_wsaa_response(wsaa_response):
    """
    Parsea la respuesta del servicio WSAA
    
    Args:
        wsaa_response: Respuesta del servicio WSAA
        
    Returns:
        dict: Información extraída (token, sign, expiration)
    """
    try:
        # Extraer datos de la respuesta
        token = wsaa_response.credentials.token
        sign = wsaa_response.credentials.sign
        
        # Parsear fecha de expiración
        expiration_str = wsaa_response.header.expirationTime
        
        # Manejar diferentes formatos de fecha
        if '.' in expiration_str and '+' in expiration_str:
            expiration = datetime.datetime.strptime(
                expiration_str, 
                "%Y-%m-%dT%H:%M:%S.%f%z"
            ).replace(tzinfo=None)
        elif '.' in expiration_str:
            expiration = datetime.datetime.strptime(
                expiration_str, 
                "%Y-%m-%dT%H:%M:%S.%f"
            )
        else:
            expiration = datetime.datetime.strptime(
                expiration_str, 
                "%Y-%m-%dT%H:%M:%S"
            )
        
        return {
            'token': token,
            'sign': sign,
            'expiration': expiration
        }
    
    except Exception as e:
        logger.error(f"Error al parsear respuesta WSAA: {str(e)}")
        raise

def format_wsfe_error(wsfe_errors):
    """
    Formatea los errores devueltos por el servicio WSFE
    
    Args:
        wsfe_errors: Objeto de errores de WSFE
        
    Returns:
        str: Mensaje de error formateado
    """
    try:
        if not wsfe_errors:
            return "Error desconocido"
        
        if hasattr(wsfe_errors, 'Err'):
            return f"Error {wsfe_errors.Err.Code}: {wsfe_errors.Err.Msg}"
        
        return str(wsfe_errors)
    
    except Exception as e:
        logger.error(f"Error al formatear errores WSFE: {str(e)}")
        return "Error al procesar la respuesta de AFIP"