import argparse
import sys
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from src.core.client import AfipClient
from src.services.wsfe import WSFEService
from src.utils.logger import setup_logger
from config import Config


def parse_arguments():
    parser = argparse.ArgumentParser(description='Sistema de Facturación Electrónica ARCA')
    
    subparsers = parser.add_subparsers(dest='comando', help='Comandos disponibles')
    
    # Comando para generar factura
    factura_parser = subparsers.add_parser('factura', help='Operaciones con facturas')
    factura_subparsers = factura_parser.add_subparsers(dest='factura_comando')
    
    # Generar factura
    generar_parser = factura_subparsers.add_parser('generar', help='Generar una nueva factura')
    generar_parser.add_argument('--tipo', type=str, required=True, choices=['A', 'B', 'C'], help='Tipo de factura')
    generar_parser.add_argument('--punto-venta', type=int, required=True, help='Punto de venta')
    generar_parser.add_argument('--concepto', type=int, required=True, choices=[1, 2, 3], 
                              help='Concepto (1: Productos, 2: Servicios, 3: Productos y Servicios)')
    generar_parser.add_argument('--tipo-doc', type=int, required=True, help='Tipo de documento del cliente')
    generar_parser.add_argument('--nro-doc', type=str, required=True, help='Número de documento del cliente')
    generar_parser.add_argument('--importe', type=float, required=True, help='Importe total de la factura')
    generar_parser.add_argument('--fecha', type=str, help='Fecha de la factura (formato: YYYYMMDD)')
    
    # Consultar factura
    consultar_parser = factura_subparsers.add_parser('consultar', help='Consultar una factura existente')
    consultar_parser.add_argument('--tipo', type=str, required=True, choices=['A', 'B', 'C'], help='Tipo de factura')
    consultar_parser.add_argument('--punto-venta', type=int, required=True, help='Punto de venta')
    consultar_parser.add_argument('--numero', type=int, required=True, help='Número de factura')
    
    # Último número de comprobante
    ultimo_parser = factura_subparsers.add_parser('ultimo', help='Obtener último número de comprobante')
    ultimo_parser.add_argument('--tipo', type=str, required=True, choices=['A', 'B', 'C'], help='Tipo de factura')
    ultimo_parser.add_argument('--punto-venta', type=int, required=True, help='Punto de venta')
    
    # Consulta de tipos de comprobantes
    subparsers.add_parser('tipos-comprobante', help='Listar tipos de comprobantes disponibles')
    
    # Consulta de puntos de venta
    subparsers.add_parser('puntos-venta', help='Listar puntos de venta habilitados')
    
    # Consulta de tipos de documento
    subparsers.add_parser('tipos-documento', help='Listar tipos de documento')
    
    # Consulta de tipos de conceptos
    subparsers.add_parser('tipos-concepto', help='Listar tipos de conceptos')
    
    # Consulta de tipos de alícuotas de IVA
    subparsers.add_parser('tipos-iva', help='Listar tipos de alícuotas de IVA')
    
    # Consulta de estado de servidores
    subparsers.add_parser('estado', help='Verificar el estado de los servidores de AFIP')
    
    # Comando para regenerar el token de autenticación
    subparsers.add_parser('regenerar-token', help='Regenerar el token de autenticación con AFIP')
    
    # Modo de ejecución
    parser.add_argument('--produccion', action='store_true', help='Ejecutar en modo producción (por defecto: homologación)')
    parser.add_argument('--config', type=str, default='config.ini', help='Archivo de configuración')
    parser.add_argument('--debug', action='store_true', help='Activar modo depuración')
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger('facturacion_afip', log_level)
    
    try:
        config = Config(args.config)
        entorno = 'produccion' if args.produccion else 'homologacion'
        logger.info(f"Ejecutando en entorno: {entorno}")
    except Exception as e:
        logger.error(f"Error al cargar la configuración: {e}")
        sys.exit(1)
    
    try:
        client = AfipClient(
            cuit=config.get('cuit'),
            cert_path=config.get('cert_path'),
            key_path=config.get('key_path'),
            production=args.produccion
        )
        wsfe = WSFEService(client)
    except Exception as e:
        logger.error(f"Error al inicializar el cliente AFIP: {e}")
        sys.exit(1)
    
    try:
        if args.comando == 'factura':
            procesar_comando_factura(args, wsfe, logger)
        elif args.comando == 'tipos-comprobante':
            tipos = wsfe.get_tipos_comprobante()
            print_tabla(tipos, ['Id', 'Descripción'])
        elif args.comando == 'puntos-venta':
            puntos = wsfe.get_puntos_venta()
            print_tabla(puntos, ['Punto de Venta', 'Tipo', 'Bloqueado'])
        elif args.comando == 'tipos-documento':
            tipos = wsfe.get_tipos_documento()
            print_tabla(tipos, ['Id', 'Descripción'])
        elif args.comando == 'tipos-concepto':
            tipos = wsfe.get_tipos_concepto()
            print_tabla(tipos, ['Id', 'Descripción'])
        elif args.comando == 'tipos-iva':
            tipos = wsfe.get_tipos_iva()
            print_tabla(tipos, ['Id', 'Descripción', 'Alícuota'])
        elif args.comando == 'estado':
            estado = wsfe.get_server_status()
            print(f"Estado del servidor WSFE: {estado['wsfe']}")
            print(f"Estado del servidor WSAA: {estado['wsaa']}")
            print(f"Estado del servidor DB: {estado['db']}")
        elif args.comando == 'regenerar-token':
            client.auth.authenticate(force=True)
            logger.info("Token regenerado con éxito")
        else:
            logger.error("Comando no reconocido")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error al ejecutar el comando: {e}")
        sys.exit(1)


def procesar_comando_factura(args, wsfe, logger):
    if args.factura_comando == 'generar':
        tipo_cbte_map = {'A': 1, 'B': 6, 'C': 11}
        tipo_comprobante = tipo_cbte_map.get(args.tipo)
        
        if not tipo_comprobante:
            logger.error(f"Tipo de factura inválido: {args.tipo}")
            return

        if args.fecha:
            try:
                fecha = datetime.strptime(args.fecha, '%Y%m%d')
            except ValueError:
                logger.error("Formato de fecha inválido. Use YYYYMMDD")
                return
        else:
            fecha = datetime.now()
        
        importe_total = Decimal(str(args.importe))
        
        imp_neto = importe_total
        imp_iva = Decimal('0')
        
        ali_iva = []
        
        if args.tipo == 'A':
            imp_neto = (importe_total / Decimal('1.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            imp_iva = importe_total - imp_neto
            
            ali_iva = [{
                'id': 5,  # Código para 21%
                'base_imp': float(imp_neto),
                'importe': float(imp_iva)
            }]

        factura_data = {
            'tipo_cbte': tipo_comprobante,
            'punto_vta': args.punto_venta,
            'concepto': args.concepto,
            'tipo_doc': args.tipo_doc,
            'nro_doc': args.nro_doc,
            'fecha_cbte': fecha.strftime('%Y%m%d'),
            'imp_total': float(importe_total),
            'imp_neto': float(imp_neto),
            'imp_iva': float(imp_iva),
            'imp_trib': 0,
            'imp_op_ex': 0,
            'fecha_serv_desde': fecha.strftime('%Y%m%d'),
            'fecha_serv_hasta': fecha.strftime('%Y%m%d'),
            'fecha_venc_pago': fecha.strftime('%Y%m%d'),
            'moneda_id': 'PES',
            'moneda_ctz': 1,
            'iva': ali_iva 
        }
        
        # Crear factura
        try:
            result = wsfe.crear_factura(factura_data)
            if result['success']:
                print(f"\nFactura generada con éxito")
            else:
                print(f"\n❌ Error AFIP: {result.get('error', 'Desconocido')}")
        except Exception as e:
            logger.error(f"Error de conexión/proceso: {e}")
    
    elif args.factura_comando == 'consultar':
        tipo_comprobante = {
            'A': 1,
            'B': 6,
            'C': 11
        }[args.tipo]
        
        result = wsfe.consultar_factura(tipo_comprobante, args.punto_venta, args.numero)
        
        if result['success']:
            print("\nDatos de la factura:")
            for k, v in result['data'].items():
                print(f"{k}: {v}")
        else:
            print(f"\nError al consultar la factura: {result['error']}")
    
    elif args.factura_comando == 'ultimo':
        tipo_comprobante = {
            'A': 1,
            'B': 6,
            'C': 11
        }[args.tipo]
        
        result = wsfe.get_ultimo_comprobante(tipo_comprobante, args.punto_venta)
        
        if result['success']:
            print(f"\nÚltimo número de comprobante para {args.tipo} - PV {args.punto_venta}: {result['number']}")
        else:
            print(f"\nError al consultar último comprobante: {result['error']}")
    
    else:
        logger.error("Comando de factura no reconocido")
        sys.exit(1)


def print_tabla(data, headers):
    if not data:
        print("No hay datos para mostrar")
        return
    
    # Determinar el ancho de cada columna
    widths = [max(len(str(item[i])) for item in data) for i in range(len(headers))]
    header_widths = [len(h) for h in headers]
    
    for i in range(len(widths)):
        widths[i] = max(widths[i], header_widths[i]) + 2
    
    # Imprimir encabezados
    header_line = '|'
    for i, header in enumerate(headers):
        header_line += f" {header.ljust(widths[i] - 1)}|"
    print(header_line)
    
    # Imprimir separador
    separator = '+'
    for width in widths:
        separator += '-' * width + '+'
    print(separator)
    
    # Imprimir datos
    for row in data:
        line = '|'
        for i, item in enumerate(row):
            line += f" {str(item).ljust(widths[i] - 1)}|"
        print(line)

if __name__ == "__main__":
    main()