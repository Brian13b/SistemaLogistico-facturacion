"""
Utilidades para manejo de certificados y firma digital
"""
import os
from OpenSSL import crypto
from base64 import b64encode

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def read_cert_and_key(cert_path, key_path):
    """
    Lee el certificado y la clave privada desde los archivos
    
    Args:
        cert_path (str): Ruta al certificado
        key_path (str): Ruta a la clave privada
        
    Returns:
        tuple: (cert_content, key_content)
    """
    try:
        # Verificar que los archivos existen
        if not os.path.exists(cert_path):
            raise FileNotFoundError(f"El certificado no existe en la ruta: {cert_path}")
        
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"La clave privada no existe en la ruta: {key_path}")
        
        # Leer archivos
        with open(cert_path, 'r') as cert_file:
            cert_content = cert_file.read()
            
        with open(key_path, 'r') as key_file:
            key_content = key_file.read()
            
        return cert_content, key_content
    
    except Exception as e:
        logger.error(f"Error al leer certificado o clave: {str(e)}")
        raise

def sign_data(data, cert_content, key_content):
    """
    Firma un mensaje usando el certificado y la clave privada
    
    Args:
        data (str): Datos a firmar
        cert_content (str): Contenido del certificado
        key_content (str): Contenido de la clave privada
        
    Returns:
        str: Mensaje firmado en formato base64
    """
    try:
        # Crear objetos de certificado y clave
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_content)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_content)
        
        # Firmar los datos
        p7 = crypto.PKCS7()
        p7.type = crypto.PKCS7_SIGNED
        p7.set_content(crypto.BIO.MemoryBuffer(data.encode('utf-8')))
        p7.sign(cert, key, [crypto.PKCS7_NOSIGS])
        
        # Convertir a base64
        out = crypto.BIO.MemoryBuffer()
        p7.write_pkcs7(out)
        return b64encode(out.read()).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Error al firmar datos: {str(e)}")
        raise

def generate_testing_cert(output_dir):
    """
    Genera certificados para pruebas
    
    Args:
        output_dir (str): Directorio donde se guardarán los certificados
        
    Returns:
        tuple: (cert_path, key_path)
    """
    try:
        # Crear directorio si no existe
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Rutas para los archivos
        key_path = os.path.join(output_dir, "clave_privada.key")
        csr_path = os.path.join(output_dir, "pedido.csr")
        cert_path = os.path.join(output_dir, "certificado.crt")
        
        # Generar clave privada
        os.system(f"openssl genrsa -out {key_path} 2048")
        
        # Generar CSR
        os.system(f'openssl req -new -key {key_path} -subj "/C=AR/O=MiOrganizacion/CN=MiNombre/serialNumber=CUIT 20123456789" -out {csr_path}')
        
        # Auto-firmar certificado
        os.system(f"openssl x509 -req -days 365 -in {csr_path} -signkey {key_path} -out {cert_path}")
        
        logger.info(f"Certificados generados exitosamente en {output_dir}")
        return cert_path, key_path
    
    except Exception as e:
        logger.error(f"Error al generar certificados: {str(e)}")
        raise