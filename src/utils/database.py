"""
Módulo para la gestión de base de datos del sistema de facturación
"""

import os
import json
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger('facturacion_afip.database')


class FacturasDB:
    """Clase para gestionar la base de datos de facturas"""
    
    def __init__(self, config):
        """
        Inicializa la conexión a la base de datos
        
        Args:
            config: Objeto de configuración con los datos de conexión
        """
        self.config = config
        
        # Opciones de conexión
        self.mongo_uri = config.get('mongo_uri', 'mongodb://localhost:27017/')
        self.db_name = config.get('mongo_db', 'facturacion_afip')
        self.collection_name = 'facturas'
        
        # Conectar a la base de datos
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.facturas = self.db[self.collection_name]
            
            # Crear índices si no existen
            self._create_indexes()
            
            logger.info(f"Conexión exitosa a la base de datos: {self.db_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"No se pudo conectar a MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Crea los índices necesarios en la colección de facturas"""
        indexes = [
            ('numero', ASCENDING),
            ('tipo_cbte', ASCENDING),
            ('punto_vta', ASCENDING),
            ('cae', ASCENDING),
            ('fecha_cbte', DESCENDING),
            ('nro_doc', ASCENDING),
            ('imp_total', ASCENDING),
        ]
        
        for field, direction in indexes:
            self.facturas.create_index([(field, direction)])
        
        # Índice compuesto para búsqueda rápida por tipo, punto de venta y número
        self.facturas.create_index([
            ('tipo_cbte', ASCENDING),
            ('punto_vta', ASCENDING),
            ('numero', ASCENDING)
        ], unique=True)
    
    def guardar_factura(self, factura_data, cae_response):
        """
        Guarda una factura emitida en la base de datos
        
        Args:
            factura_data: Datos de la factura enviada a AFIP
            cae_response: Respuesta con el CAE obtenido de AFIP
            
        Returns:
            ObjectId: ID del documento insertado
        """
        # Crear documento para MongoDB
        factura_doc = {
            # Datos generales
            'numero': cae_response['cae_data']['numero'],
            'tipo_cbte': factura_data['tipo_cbte'],
            'punto_vta': factura_data['punto_vta'],
            'fecha_cbte': factura_data['fecha_cbte'],
            'concepto': factura_data['concepto'],
            
            # Datos del cliente
            'tipo_doc': factura_data['tipo_doc'],
            'nro_doc': factura_data['nro_doc'],
            
            # Importes
            'imp_total': factura_data['imp_total'],
            'imp_neto': factura_data['imp_neto'],
            'imp_iva': factura_data.get('imp_iva', 0),
            'imp_trib': factura_data.get('imp_trib', 0),
            'imp_op_ex': factura_data.get('imp_op_ex', 0),
            
            # Datos del CAE
            'cae': cae_response['cae_data']['cae'],
            'fecha_vto_cae': cae_response['cae_data']['fecha_vto'],
            
            # Datos de trazabilidad
            'fecha_creacion': datetime.now().isoformat(),
            'original_request': factura_data,
            'afip_response': cae_response,
            
            # Estado del PDF
            'pdf_generado': False,
            'pdf_path': None
        }
        
        # Guardar en MongoDB
        try:
            result = self.facturas.insert_one(factura_doc)
            logger.info(f"Factura guardada en base de datos con ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error al guardar factura en base de datos: {e}")
            raise
    
    def actualizar_factura(self, filtro, datos):
        """
        Actualiza los datos de una factura existente
        
        Args:
            filtro: Diccionario con los criterios de búsqueda
            datos: Datos a actualizar
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            result = self.facturas.update_one(filtro, {'$set': datos})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error al actualizar factura: {e}")
            return False
    
    def buscar_factura(self, tipo_cbte, punto_vta, numero):
        """
        Busca una factura específica
        
        Args:
            tipo_cbte: Tipo de comprobante
            punto_vta: Punto de venta
            numero: Número de comprobante
            
        Returns:
            dict: Datos de la factura o None si no existe
        """
        try:
            factura = self.facturas.find_one({
                'tipo_cbte': tipo_cbte,
                'punto_vta': punto_vta,
                'numero': numero
            })
            return factura
        except Exception as e:
            logger.error(f"Error al buscar factura: {e}")
            return None
    
    def buscar_factura_por_cae(self, cae):
        """
        Busca una factura por su CAE
        
        Args:
            cae: Código de Autorización Electrónico
            
        Returns:
            dict: Datos de la factura o None si no existe
        """
        try:
            factura = self.facturas.find_one({'cae': cae})
            return factura
        except Exception as e:
            logger.error(f"Error al buscar factura por CAE: {e}")
            return None
    
    def listar_facturas(self, filtros=None, limite=50, pagina=1, ordenar_por='fecha_cbte', orden=-1):
        """
        Lista las facturas aplicando filtros
        
        Args:
            filtros: Diccionario con filtros a aplicar
            limite: Cantidad máxima de resultados
            pagina: Número de página (para paginación)
            ordenar_por: Campo por el cual ordenar
            orden: 1 para ascendente, -1 para descendente
            
        Returns:
            list: Lista de facturas
        """
        try:
            if filtros is None:
                filtros = {}
                
            # Aplicar salto para paginación
            skip = (pagina - 1) * limite
            
            # Obtener facturas
            cursor = self.facturas.find(
                filtros,
                {
                    'numero': 1,
                    'tipo_cbte': 1, 
                    'punto_vta': 1,
                    'fecha_cbte': 1,
                    'nro_doc': 1,
                    'imp_total': 1,
                    'cae': 1,
                    'pdf_generado': 1
                }
            ).sort(ordenar_por, orden).skip(skip).limit(limite)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"Error al listar facturas: {e}")
            return []
    
    def obtener_estadisticas(self, desde=None, hasta=None):
        """
        Obtiene estadísticas de facturación
        
        Args:
            desde: Fecha de inicio (formato YYYYMMDD)
            hasta: Fecha de fin (formato YYYYMMDD)
            
        Returns:
            dict: Estadísticas de facturación
        """
        try:
            # Construir filtro de fechas
            filtro = {}
            if desde:
                filtro['fecha_cbte'] = {'$gte': desde}
            if hasta:
                if 'fecha_cbte' in filtro:
                    filtro['fecha_cbte']['$lte'] = hasta
                else:
                    filtro['fecha_cbte'] = {'$lte': hasta}
            
            # Pipeline de agregación
            pipeline = [
                {'$match': filtro},
                {'$group': {
                    '_id': '$tipo_cbte',
                    'cantidad': {'$sum': 1},
                    'total_facturado': {'$sum': '$imp_total'},
                    'total_neto': {'$sum': '$imp_neto'},
                    'total_iva': {'$sum': '$imp_iva'}
                }},
                {'$sort': {'_id': 1}}
            ]
            
            resultados = list(self.facturas.aggregate(pipeline))
            
            # Calcular totales generales
            total_facturas = sum(r['cantidad'] for r in resultados)
            total_facturado = sum(r['total_facturado'] for r in resultados)
            
            return {
                'por_tipo': resultados,
                'total_facturas': total_facturas,
                'total_facturado': total_facturado
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {'error': str(e)}
    
    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Conexión a base de datos cerrada")