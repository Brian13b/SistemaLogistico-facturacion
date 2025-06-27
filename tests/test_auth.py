"""
Tests para el módulo de autenticación con AFIP
"""

import unittest
import os
import tempfile
from unittest import mock
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from src.core.auth import AfipAuth
from src.utils.cert_utils import create_ticket_request


class TestAfipAuth(unittest.TestCase):
    """Pruebas para el módulo de autenticación de AFIP"""

    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Crear archivos temporales para los certificados
        self.cert_fd, self.cert_path = tempfile.mkstemp()
        self.key_fd, self.key_path = tempfile.mkstemp()
        self.token_fd, self.token_path = tempfile.mkstemp()
        
        # Escribir datos de prueba en los archivos
        with open(self.cert_path, 'w') as f:
            f.write("-----BEGIN CERTIFICATE-----\nTEST CERTIFICATE\n-----END CERTIFICATE-----")
        
        with open(self.key_path, 'w') as f:
            f.write("-----BEGIN PRIVATE KEY-----\nTEST PRIVATE KEY\n-----END PRIVATE KEY-----")
        
        # Datos de prueba para el token
        expiration_time = datetime.now() + timedelta(hours=10)
        token_data = {
            'token': 'test_token',
            'sign': 'test_sign',
            'expiration': expiration_time.isoformat(),
            'service': 'wsfe'
        }
        
        # Escribir token de prueba
        with open(self.token_path, 'w') as f:
            f.write(str(token_data))
        
        # Crear instancia de autenticación para pruebas
        self.cuit = '20123456789'
        self.auth = AfipAuth(
            cuit=self.cuit,
            cert_path=self.cert_path,
            key_path=self.key_path,
            production=False
        )
        
        # Sobreescribir ruta del token para pruebas
        self.auth.token_path = self.token_path

    def tearDown(self):
        """Limpieza después de cada prueba"""
        os.close(self.cert_fd)
        os.close(self.key_fd)
        os.close(self.token_fd)
        os.unlink(self.cert_path)
        os.unlink(self.key_path)
        os.unlink(self.token_path)

    def test_init(self):
        """Prueba de inicialización correcta"""
        self.assertEqual(self.auth.cuit, self.cuit)
        self.assertEqual(self.auth.cert_path, self.cert_path)
        self.assertEqual(self.auth.key_path, self.key_path)
        self.assertFalse(self.auth.production)
        self.assertEqual(self.auth.wsaa_url, AfipAuth.WSAA_URL_TESTING)

    def test_init_production(self):
        """Prueba de inicialización en modo producción"""
        auth = AfipAuth(
            cuit=self.cuit,
            cert_path=self.cert_path,
            key_path=self.key_path,
            production=True
        )
        self.assertTrue(auth.production)
        self.assertEqual(auth.wsaa_url, AfipAuth.WSAA_URL_PRODUCTION)

    @mock.patch('src.core.auth.create_ticket_request')
    @mock.patch('src.core.auth.requests.post')
    def test_authenticate(self, mock_post, mock_create_ticket):
        """Prueba el proceso de autenticación"""
        # Configurar el mock para create_ticket_request
        mock_create_ticket.return_value = "TEST_TICKET_REQUEST"
        
        # Configurar respuesta XML de ejemplo para el servicio WSAA
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <loginCmsResponse>
          <header>
            <source>CN=wsaa, O=AFIP, C=AR, SERIALNUMBER=CUIT 33693450239</source>
            <destination>SERIALNUMBER=CUIT 20123456789, CN=test</destination>
            <uniqueId>123456789</uniqueId>
            <expirationTime>2024-01-01T12:00:00.000-03:00</expirationTime>
            <generationTime>2023-12-31T12:00:00.000-03:00</generationTime>
          </header>
          <credentials>
            <token>TOKEN_TEST_12345</token>
            <sign>SIGN_TEST_12345</sign>
          </credentials>
        </loginCmsResponse>"""
        
        # Configurar el mock para la respuesta HTTP
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = response_xml
        mock_post.return_value = mock_response
        
        # Llamar al método a probar
        result = self.auth.authenticate(service='wsfe', force=True)
        
        # Verificar que los mocks fueron llamados correctamente
        mock_create_ticket.assert_called_once_with(
            self.cert_path, 
            self.key_path, 
            'wsfe',
            mock.ANY  # No verificamos el tiempo exacto
        )
        
        mock_post.assert_called_once_with(
            self.auth.wsaa_url,
            data=mock_create_ticket.return_value,
            headers={'Content-Type': 'text/xml'},
            verify=True
        )
        
        # Verificar el resultado
        self.assertTrue(result)
        self.assertEqual(self.auth.token, 'TOKEN_TEST_12345')
        self.assertEqual(self.auth.sign, 'SIGN_TEST_12345')
        
        # Verificar que la fecha de expiración se estableció correctamente
        self.assertIsNotNone(self.auth.expiration)

    def test_token_valid(self):
        """Prueba la validación de un token existente"""
        # Configurar un token válido
        expiration_time = datetime.now() + timedelta(hours=10)
        self.auth.token = 'test_token'
        self.auth.sign = 'test_sign'
        self.auth.expiration = expiration_time
        self.auth.service = 'wsfe'
        
        # Verificar que el token es válido
        self.assertTrue(self.auth.is_token_valid('wsfe'))
        
        # Cambiar el servicio y verificar que ahora es inválido
        self.assertFalse(self.auth.is_token_valid('wsfev1'))
        
        # Cambiar la expiración y verificar que ahora es inválido
        self.auth.service = 'wsfe'
        self.auth.expiration = datetime.now() - timedelta(hours=1)
        self.assertFalse(self.auth.is_token_valid('wsfe'))

    def test_get_auth_headers(self):
        """Prueba la obtención de los headers de autenticación"""
        # Configurar un token
        self.auth.token = 'test_token'
        self.auth.sign = 'test_sign'
        
        # Obtener los headers
        headers = self.auth.get_auth_headers()
        
        # Verificar los headers
        self.assertEqual(headers['Auth']['Token'], 'test_token')
        self.assertEqual(headers['Auth']['Sign'], 'test_sign')
        self.assertEqual(headers['Auth']['Cuit'], self.cuit)


if __name__ == '__main__':
    unittest.main()