"""
Utilidades para manejo de certificados y firma digital (usa cryptography para PKCS7)
"""
import os
from typing import Optional, Tuple
from base64 import b64encode

from src.utils.logger import setup_logger
logger = setup_logger(__name__)

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7, load_pem_private_key, load_der_private_key

def _load_cert_any(buf: bytes) -> x509.Certificate:
    """
    Intenta cargar un certificado en PEM o DER.
    """
    try:
        return x509.load_pem_x509_certificate(buf)
    except Exception:
        return x509.load_der_x509_certificate(buf)

def _load_key_any(buf: bytes, password: Optional[bytes] = None):
    """
    Intenta cargar una clave privada en PEM o DER (PKCS#8).
    """
    try:
        return load_pem_private_key(buf, password=password)
    except Exception:
        return load_der_private_key(buf, password=password)

def read_cert_and_key(cert_path: str, key_path: str) -> Tuple[bytes, bytes]:
    """
    Lee el certificado y la clave privada desde los archivos y devuelve bytes.
    
    Args:
        cert_path (str): Ruta al certificado
        key_path (str): Ruta a la clave privada
        
    Returns:
        tuple: (cert_bytes, key_bytes)
    """
    try:
        if not os.path.exists(cert_path):
            raise FileNotFoundError(f"El certificado no existe en la ruta: {cert_path}")
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"La clave privada no existe en la ruta: {key_path}")

        with open(cert_path, 'rb') as cert_file:
            cert_content = cert_file.read()
        with open(key_path, 'rb') as key_file:
            key_content = key_file.read()

        return cert_content, key_content

    except Exception as e:
        logger.error(f"Error al leer certificado o clave: {str(e)}")
        raise

def sign_data(data, cert_content: bytes, key_content: bytes, password: Optional[bytes] = None, detached: bool = True, hash_algo: str = "sha256") -> str:
    """
    Firma un mensaje usando el certificado y la clave privada y devuelve PKCS7 (DER) codificado en base64.
    
    Args:
        data (str|bytes): Datos a firmar
        cert_content (bytes): Contenido del certificado (PEM o DER)
        key_content (bytes): Contenido de la clave privada (PEM o DER)
        password (Optional[bytes]): Password de la clave si está cifrada
        detached (bool): True para firma detached (por defecto). Ajustar según el servicio.
        
    Returns:
        str: PKCS7 (DER) codificado en base64
    """
    try:
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        cert = _load_cert_any(cert_content)
        private_key = _load_key_any(key_content, password=password)

        # seleccionar algoritmo de digest
        algo = hash_algo.lower()
        if algo == "sha1":
            digest = hashes.SHA1()
        elif algo == "sha256":
            digest = hashes.SHA256()
        elif algo == "sha384":
            digest = hashes.SHA384()
        elif algo == "sha512":
            digest = hashes.SHA512()
        else:
            raise ValueError("hash_algo no soportado")
        
        builder = pkcs7.PKCS7SignatureBuilder().set_data(data_bytes)
        builder = builder.add_signer(cert, private_key, digest)

        options = [pkcs7.PKCS7Options.DetachedSignature] if detached else []
        signed_der = builder.sign(serialization.Encoding.DER, options)

        return b64encode(signed_der).decode('utf-8')

    except Exception as e:
        logger.error(f"Error al firmar datos: {str(e)}")
        raise

def sign_from_files(cert_path: str, key_path: str, data, password: Optional[bytes] = None, detached: bool = True) -> str:
    """
    Conveniencia: lee cert y key desde disco y firma los datos.
    """
    cert_bytes, key_bytes = read_cert_and_key(cert_path, key_path)
    return sign_data(data, cert_bytes, key_bytes, password=password, detached=detached)

def generate_testing_cert(output_dir: str) -> Tuple[str, str]:
    """
    Genera certificados para pruebas usando openssl (requiere openssl en el host/imagen).
    
    Args:
        output_dir (str): Directorio donde se guardarán los certificados
        
    Returns:
        tuple: (cert_path, key_path)
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        key_path = os.path.join(output_dir, "clave_privada.key")
        csr_path = os.path.join(output_dir, "pedido.csr")
        cert_path = os.path.join(output_dir, "certificado.crt")
        
        # Generar clave privada, CSR y certificado autofirmado
        os.system(f"openssl genrsa -out \"{key_path}\" 2048")
        os.system(f'openssl req -new -key "{key_path}" -subj "/C=AR/O=MiOrganizacion/CN=MiNombre/serialNumber=CUIT 20123456789" -out "{csr_path}"')
        os.system(f"openssl x509 -req -days 365 -in \"{csr_path}\" -signkey \"{key_path}\" -out \"{cert_path}\"")
        
        logger.info(f"Certificados generados exitosamente en {output_dir}")
        return cert_path, key_path

    except Exception as e:
        logger.error(f"Error al generar certificados: {str(e)}")
        raise