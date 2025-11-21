import os
from base64 import b64encode
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def read_cert_and_key(cert_path, key_path):
    """Lee certificado y clave desde disco"""
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Certificado no encontrado: {cert_path}")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Clave privada no encontrada: {key_path}")
        
    with open(cert_path, "rb") as f:
        cert_data = f.read()
    with open(key_path, "rb") as f:
        key_data = f.read()
        
    return cert_data, key_data

def sign_data(data, cert_content, key_content, detached):
    """
    Firma datos (TRA) usando PKCS#7 Detached signature
    Compatible con WSAA de AFIP
    """
    try:
        # Cargar certificado
        cert = x509.load_pem_x509_certificate(cert_content)
        
        # Cargar clave privada
        key = serialization.load_pem_private_key(
            key_content,
            password=None
        )
        
        # Configurar opciones de firma
        options = [pkcs7.PKCS7Options.DetachedSignature] if detached else []
        
        # Construir firma
        builder = pkcs7.PKCS7SignatureBuilder()\
            .set_data(data.encode('utf-8') if isinstance(data, str) else data)\
            .add_signer(cert, key, hashes.SHA256()) # AFIP soporta SHA256
            
        # Generar PKCS7 (DER)
        signed_data = builder.sign(
            encoding=serialization.Encoding.DER,
            options=options
        )
        
        # Retornar en Base64 como pide AFIP
        return b64encode(signed_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error firmando datos: {e}")
        raise