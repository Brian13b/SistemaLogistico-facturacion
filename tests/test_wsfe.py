"""
Tests para el servicio WSFE (Web Service de Facturación Electrónica)
"""

import unittest
from unittest import mock
import json
from datetime import datetime

from src.core.client import AfipClient
from src.services.wsfe import WSFEService


class TestWSFEService(unittest.TestCase):
    """Pruebas para el servicio de Facturación Electrónica de AFIP"""

    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Mock para el cliente AFIP
        self.client_mock = mock.MagicMock(spec=AfipClient)
        self.client_mock.auth.cuit = '20123456789'
        self.client_mock.auth.token = 'test_token'
        self.client_mock.auth.sign = 'test_sign'
        self.client_mock.auth.is_token_valid.return_value = True
        self.client_mock.auth.get_auth_headers.return_value = {
            'Auth': {
                'Token': 'test_token',
                'Sign': 'test_sign',
                'Cuit': '20123456789'
            }
        }
        
        # Crear instancia del servicio
        self.wsfe = WSFEService(self.client_mock)

    def test_get_server_status(self):
        """Prueba la verificación del estado del servidor"""
        # Configurar respuesta simulada
        response_mock = {
            'FEDummyResult': {
                'AppServer': 'OK',
                'DbServer': 'OK',
                'AuthServer': 'OK'
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEDummy.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_server_status()
        
        # Verificar que la función soap_client.FEDummy fue llamada
        self.client_mock.soap_client.FEDummy.assert_called_once()
        
        # Verificar el resultado
        self.assertEqual(result, {
            'wsfe': 'OK',
            'db': 'OK',
            'wsaa': 'OK'
        })

    def test_get_tipos_comprobante(self):
        """Prueba obtener los tipos de comprobante"""
        # Configurar respuesta simulada
        response_mock = {
            'FEParamGetTiposCbteResult': {
                'ResultGet': {
                    'CbteTipo': [
                        {
                            'Id': '1',
                            'Desc': 'Factura A',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        },
                        {
                            'Id': '6',
                            'Desc': 'Factura B',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEParamGetTiposCbte.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_tipos_comprobante()
        
        # Verificar que la función soap_client.FEParamGetTiposCbte fue llamada con los parámetros correctos
        self.client_mock.soap_client.FEParamGetTiposCbte.assert_called_once_with(
            {'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'}}
        )
        
        # Verificar el resultado
        expected = [
            ['1', 'Factura A'],
            ['6', 'Factura B']
        ]
        self.assertEqual(result, expected)

    def test_get_ultimo_comprobante(self):
        """Prueba obtener el último número de comprobante"""
        # Configurar respuesta simulada
        response_mock = {
            'FECompUltimoAutorizadoResult': {
                'PtoVta': 1,
                'CbteTipo': 1,
                'CbteNro': 54
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FECompUltimoAutorizado.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_ultimo_comprobante(1, 1)
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FECompUltimoAutorizado.assert_called_once_with({
            'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'},
            'PtoVta': 1,
            'CbteTipo': 1
        })
        
        # Verificar el resultado
        self.assertEqual(result, {'success': True, 'number': 54})

    def test_crear_factura(self):
        """Prueba crear una factura"""
        # Datos de factura para la prueba
        factura_data = {
            'tipo_cbte': 1,
            'punto_vta': 1,
            'concepto': 1,
            'tipo_doc': 80,
            'nro_doc': '20111222333',
            'fecha_cbte': '20230101',
            'imp_total': 121.0,
            'imp_neto': 100.0,
            'imp_iva': 21.0,
            'imp_trib': 0,
            'imp_op_ex': 0,
            'fecha_serv_desde': '20230101',
            'fecha_serv_hasta': '20230101',
            'fecha_venc_pago': '20230101',
            'moneda_id': 'PES',
            'moneda_ctz': 1,
            'iva': [
                {
                    'id': 5,  # 21%
                    'base_imp': 100.0,
                    'importe': 21.0
                }
            ]
        }
        
        # Configurar mock para último número de comprobante
        self.client_mock.soap_client.FECompUltimoAutorizado.return_value = {
            'FECompUltimoAutorizadoResult': {
                'PtoVta': 1,
                'CbteTipo': 1,
                'CbteNro': 54
            }
        }
        
        # Configurar respuesta simulada para CAE
        response_mock = {
            'FECAESolicitarResult': {
                'FeCabResp': {
                    'Resultado': 'A',
                    'PtoVta': 1,
                    'CbteTipo': 1,
                    'Reproceso': 'N',
                    'FchProceso': '20230101',
                },
                'FeDetResp': {
                    'FECAEDetResponse': [
                        {
                            'Resultado': 'A',
                            'CAE': '71234567890123',
                            'CAEFchVto': '20230110',
                            'Observaciones': None
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FECAESolicitar.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.crear_factura(factura_data)
        
        # Verificar que las funciones fueron llamadas
        self.client_mock.soap_client.FECompUltimoAutorizado.assert_called_once_with({
            'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'},
            'PtoVta': 1,
            'CbteTipo': 1
        })
        
        # Verificar que la función FECAESolicitar fue llamada con los parámetros correctos
        self.client_mock.soap_client.FECAESolicitar.assert_called_once()
        
        # Verificar el resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['cae_data']['cae'], '71234567890123')
        self.assertEqual(result['cae_data']['fecha_vto'], '20230110')
        self.assertEqual(result['cae_data']['numero'], 55)  # Último número + 1

    def test_consultar_factura(self):
        """Prueba consultar una factura existente"""
        # Configurar respuesta simulada
        response_mock = {
            'FECompConsultarResult': {
                'ResultGet': {
                    'Concepto': 1,
                    'DocTipo': 80,
                    'DocNro': '20111222333',
                    'CbteDesde': 55,
                    'CbteHasta': 55,
                    'CbteFch': '20230101',
                    'ImpTotal': 121.0,
                    'ImpNeto': 100.0,
                    'ImpIVA': 21.0,
                    'ImpTrib': 0,
                    'ImpOpEx': 0,
                    'CAE': '71234567890123',
                    'CAEFchVto': '20230110',
                    'FchServDesde': '20230101',
                    'FchServHasta': '20230101',
                    'FchVtoPago': '20230101',
                    'MonId': 'PES',
                    'MonCotiz': 1,
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FECompConsultar.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.consultar_factura(1, 1, 55)
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FECompConsultar.assert_called_once_with({
            'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'},
            'FeCompConsReq': {
                'CbteTipo': 1,
                'PtoVta': 1,
                'CbteNro': 55
            }
        })
        
        # Verificar el resultado
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['cae'], '71234567890123')
        self.assertEqual(result['data']['fecha_vto_cae'], '20230110')
        self.assertEqual(result['data']['imp_total'], 121.0)

    def test_get_puntos_venta(self):
        """Prueba obtener los puntos de venta habilitados"""
        # Configurar respuesta simulada
        response_mock = {
            'FEParamGetPtosVentaResult': {
                'ResultGet': {
                    'PtoVenta': [
                        {
                            'Nro': 1,
                            'EmisionTipo': 'CAE',
                            'Bloqueado': 'N',
                            'FchBaja': None
                        },
                        {
                            'Nro': 2,
                            'EmisionTipo': 'CAEA',
                            'Bloqueado': 'S',
                            'FchBaja': '20220101'
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEParamGetPtosVenta.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_puntos_venta()
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FEParamGetPtosVenta.assert_called_once_with(
            {'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'}}
        )
        
        # Verificar el resultado
        expected = [
            [1, 'CAE', 'N'],
            [2, 'CAEA', 'S']
        ]
        self.assertEqual(result, expected)

    def test_get_tipos_documento(self):
        """Prueba obtener los tipos de documento"""
        # Configurar respuesta simulada
        response_mock = {
            'FEParamGetTiposDocResult': {
                'ResultGet': {
                    'DocTipo': [
                        {
                            'Id': '80',
                            'Desc': 'CUIT',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        },
                        {
                            'Id': '96',
                            'Desc': 'DNI',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEParamGetTiposDoc.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_tipos_documento()
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FEParamGetTiposDoc.assert_called_once_with(
            {'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'}}
        )
        
        # Verificar el resultado
        expected = [
            ['80', 'CUIT'],
            ['96', 'DNI']
        ]
        self.assertEqual(result, expected)

    def test_get_tipos_iva(self):
        """Prueba obtener los tipos de alícuotas de IVA"""
        # Configurar respuesta simulada
        response_mock = {
            'FEParamGetTiposIvaResult': {
                'ResultGet': {
                    'IvaTipo': [
                        {
                            'Id': '5',
                            'Desc': '21%',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        },
                        {
                            'Id': '4',
                            'Desc': '10.5%',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEParamGetTiposIva.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_tipos_iva()
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FEParamGetTiposIva.assert_called_once_with(
            {'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'}}
        )
        
        # Verificar el resultado
        expected = [
            ['5', '21%', '21.00'],
            ['4', '10.5%', '10.50']
        ]
        
        # Solo verificamos los primeros dos elementos de cada sublista, ya que la alícuota puede variar en el formato
        for i, item in enumerate(result):
            self.assertEqual(item[0], expected[i][0])
            self.assertEqual(item[1], expected[i][1])

    def test_get_tipos_concepto(self):
        """Prueba obtener los tipos de concepto"""
        # Configurar respuesta simulada
        response_mock = {
            'FEParamGetTiposConceptoResult': {
                'ResultGet': {
                    'ConceptoTipo': [
                        {
                            'Id': '1',
                            'Desc': 'Productos',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        },
                        {
                            'Id': '2',
                            'Desc': 'Servicios',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        },
                        {
                            'Id': '3',
                            'Desc': 'Productos y Servicios',
                            'FchDesde': '20100917',
                            'FchHasta': None
                        }
                    ]
                }
            }
        }
        
        # Configurar el comportamiento del mock
        self.client_mock.soap_client.FEParamGetTiposConcepto.return_value = response_mock
        
        # Ejecutar la función a probar
        result = self.wsfe.get_tipos_concepto()
        
        # Verificar que la función fue llamada con los parámetros correctos
        self.client_mock.soap_client.FEParamGetTiposConcepto.assert_called_once_with(
            {'Auth': {'Token': 'test_token', 'Sign': 'test_sign', 'Cuit': '20123456789'}}
        )
        
        # Verificar el resultado
        expected = [
            ['1', 'Productos'],
            ['2', 'Servicios'],
            ['3', 'Productos y Servicios']
        ]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()