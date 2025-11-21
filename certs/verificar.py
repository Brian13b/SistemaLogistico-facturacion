from cryptography import x509
from cryptography.hazmat.primitives import serialization

def cargar_archivos():
    try:
        print("Leyendo certificado.crt...")
        with open("certificado.crt", "rb") as f:
            cert_bytes = f.read()
            cert = x509.load_pem_x509_certificate(cert_bytes)

        print("Leyendo clave_privada.key...")
        with open("clave_privada.key", "rb") as f:
            key_bytes = f.read()
            private_key = serialization.load_pem_private_key(key_bytes, password=None)

        # Obtener las claves públicas de ambos
        pub_cert = cert.public_key().public_numbers()
        pub_key = private_key.public_key().public_numbers()

        print("\n--- RESULTADO ---")
        if pub_cert == pub_key:
            print("✅ ¡ÉXITO! La clave privada COINCIDE con el certificado.")
            print("El problema NO son los archivos. Es probable que AFIP requiera vincular el certificado nuevamente.")
        else:
            print("❌ ERROR: La clave privada NO coincide con el certificado.")
            print("Esta es la causa del error 'Firma inválida'.")
            print("SOLUCIÓN: Debes generar un nuevo CSR y obtener un nuevo certificado en AFIP.")

    except Exception as e:
        print(f"\n❌ Error leyendo archivos: {e}")
        print("Asegúrate de que los archivos se llamen 'certificado.crt' y 'clave_privada.key' y tengan los encabezados -----BEGIN...")

if __name__ == "__main__":
    cargar_archivos()