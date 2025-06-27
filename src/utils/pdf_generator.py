#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generador de PDF para las facturas electrónicas de AFIP
"""

import os
import logging
import qrcode
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
import json
import base64

logger = logging.getLogger('facturacion_afip.pdf')


class FacturaPDF:
    """Clase para generar PDFs de facturas electrónicas"""
    
    # Mapeo de tipos de comprobante a nombres
    TIPOS_COMPROBANTE = {
        1: "FACTURA A",
        2: "NOTA DE DÉBITO A",
        3: "NOTA DE CRÉDITO A",
        6: "FACTURA B",
        7: "NOTA DE DÉBITO B",
        8: "NOTA DE CRÉDITO B",
        11: "FACTURA C",
        12: "NOTA DE DÉBITO C",
        13: "NOTA DE CRÉDITO C"
    }
    
    # Mapeo de tipos de documento
    TIPOS_DOCUMENTO = {
        80: "CUIT",
        86: "CUIL",
        96: "DNI",
        99: "Consumidor Final"
    }
    
    def __init__(self, config):
        """
        Inicializa el generador de PDF
        
        Args:
            config: Objeto de configuración
        """
        self.config = config
        self.output_dir = config.get('pdf_output_dir', 'facturas_pdf')
        
        # Crear directorio si no existe
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Datos de la empresa
        self.empresa = {
            'razon_social': config.get('razon_social', 'EMPRESA S.A.'),
            'domicilio': config.get('domicilio', 'Calle Falsa 123'),
            'localidad': config.get('localidad', 'Ciudad'),
            'provincia': config.get('provincia', 'Provincia'),
            'cp': config.get('cp', '1000'),
            'cuit': config.get('cuit', '20123456789'),
            'inicio_actividades': config.get('inicio_actividades', '01/01/2020'),
            'condicion_iva': config.get('condicion_iva', 'IVA Responsable Inscripto'),
            'ingresos_brutos': config.get('ingresos_brutos', ''),
            'logo_path': config.get('logo_path', None)
        }
        
    def generar_pdf(self, factura_data):
        """
        Genera un PDF para una factura
        
        Args:
            factura_data: Datos de la factura (desde la base de datos)
            
        Returns:
            str: Ruta al archivo PDF generado
        """
        try:
            # Nombre de archivo con tipo, punto de venta y número
            tipo_cbte_letra = self._get_tipo_comprobante_letra(factura_data['tipo_cbte'])
            filename = f"{tipo_cbte_letra}_{factura_data['punto_vta']:04d}_{factura_data['numero']:08d}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            # Crear el documento PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm
            )
            
            # Crear elementos del documento
            elements = []
            
            # Encabezado
            elements.extend(self._crear_encabezado(factura_data))
            
            # Datos del cliente
            elements.extend(self._crear_datos_cliente(factura_data))
            
            # Detalles de la factura
            elements.extend(self._crear_detalles_factura(factura_data))
            
            # Totales
            elements.extend(self._crear_totales(factura_data))
            
            # Datos del CAE
            elements.extend(self._crear_datos_cae(factura_data))
            
            # Construir el documento
            doc.build(elements, onFirstPage=self._agregar_metadata)
            
            logger.info(f"PDF generado correctamente: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error al generar PDF: {e}")
            raise
    
    def _get_tipo_comprobante_letra(self, tipo_cbte):
        """Obtiene la letra del tipo de comprobante"""
        if tipo_cbte in [1, 2, 3]:
            return "A"
        elif tipo_cbte in [6, 7, 8]:
            return "B"
        elif tipo_cbte in [11, 12, 13]:
            return "C"
        return "X"  # Desconocido
    
    def _agregar_metadata(self, canvas, doc):
        """Agrega metadatos al PDF"""
        canvas.setTitle(f"Factura {self._get_tipo_comprobante_letra(self.factura_actual['tipo_cbte'])}")
        canvas.setAuthor(self.empresa['razon_social'])
        canvas.setSubject("Factura Electrónica AFIP")
    
    def _crear_encabezado(self, factura_data):
        """Crea el encabezado de la factura"""
        elements = []
        
        # Guardar referencia a la factura actual para usar en otros métodos
        self.factura_actual = factura_data
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        
        # Título de factura con letra grande
        tipo_cbte_nombre = self.TIPOS_COMPROBANTE.get(factura_data['tipo_cbte'], "COMPROBANTE")
        tipo_cbte_letra = self._get_tipo_comprobante_letra(factura_data['tipo_cbte'])
        
        # Crear tabla de 3 columnas para el encabezado
        data = [
            # Fila 1: Logo, Tipo de comprobante, Datos fiscales
            [
                # Logo de la empresa
                self._get_logo_image() if self.empresa['logo_path'] else "",
                
                # Tipo de comprobante
                [
                    Paragraph(f"<b>{tipo_cbte_letra}</b>", ParagraphStyle(name='FacturaLetra', fontSize=36, alignment=1)),
                    Spacer(1, 5*mm),
                    Paragraph(f"<b>Cod. {factura_data['tipo_cbte']}</b>", ParagraphStyle(name='CodigoFactura', fontSize=10, alignment=1))
                ],
                
                # Datos fiscales
                [
                    Paragraph(f"<b>{tipo_cbte_nombre}</b>", ParagraphStyle(name='TipoComp', fontSize=14, alignment=1)),
                    Paragraph(f"<b>N°: {factura_data['punto_vta']:04d}-{factura_data['numero']:08d}</b>", ParagraphStyle(name='NumComp', fontSize=12, alignment=1)),
                    Spacer(1, 5*mm),
                    Paragraph(f"Fecha de emisión: {self._formatear_fecha(factura_data['fecha_cbte'])}", ParagraphStyle(name='FechaComp', fontSize=10, alignment=1))
                ]
            ],
        ]
        
        # Crear tabla
        header_table = Table(data, colWidths=[4*cm, 4*cm, 10*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # Datos de la empresa
        data = [
            [Paragraph(f"<b>{self.empresa['razon_social']}</b>", normal_style)],
            [Paragraph(f"Domicilio: {self.empresa['domicilio']} - {self.empresa['localidad']} - {self.empresa['provincia']} ({self.empresa['cp']})", normal_style)],
            [Paragraph(f"CUIT: {self.empresa['cuit']} - {self.empresa['condicion_iva']}", normal_style)],
            [Paragraph(f"Ingresos Brutos: {self.empresa['ingresos_brutos']} - Inicio de actividades: {self.empresa['inicio_actividades']}", normal_style)]
        ]
        
        empresa_table = Table(data, colWidths=[18*cm])
        empresa_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(empresa_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _get_logo_image(self):
        """Obtiene la imagen del logo de la empresa"""
        if not self.empresa['logo_path'] or not os.path.exists(self.empresa['logo_path']):
            return None
            
        try:
            logo = Image(self.empresa['logo_path'])
            logo.drawHeight = 2*cm
            logo.drawWidth = 4*cm
            return logo
        except Exception as e:
            logger.error(f"Error al cargar logo: {e}")
            return None
    
    def _crear_datos_cliente(self, factura_data):
        """Crea la sección de datos del cliente"""
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Tipo de documento formateado
        tipo_doc_nombre = self.TIPOS_DOCUMENTO.get(factura_data['tipo_doc'], "Doc")
        
        # Datos del cliente
        data = [
            [Paragraph("<b>CLIENTE</b>", normal_style), "", ""],
            [Paragraph(f"{tipo_doc_nombre}:", normal_style), Paragraph(f"{factura_data['nro_doc']}", normal_style), ""],
            [Paragraph("Condición IVA:", normal_style), Paragraph("Consumidor Final", normal_style), ""]
        ]
        
        # Crear tabla
        cliente_table = Table(data, colWidths=[4*cm, 7*cm, 7*cm])
        cliente_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(cliente_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _crear_detalles_factura(self, factura_data):
        """Crea la sección de detalles de la factura"""
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Cabecera de tabla de detalles
        data = [
            [
                Paragraph("<b>Código</b>", normal_style),
                Paragraph("<b>Descripción</b>", normal_style),
                Paragraph("<b>Cant.</b>", normal_style),
                Paragraph("<b>Precio Unit.</b>", normal_style),
                Paragraph("<b>Subtotal</b>", normal_style)
            ]
        ]
        
        # Como no tenemos detalles en este ejemplo, agregamos una fila con descripción genérica
        concepto_map = {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}
        concepto_desc = concepto_map.get(factura_data['concepto'], "Concepto")
        
        data.append([
            Paragraph("001", normal_style),
            Paragraph(f"{concepto_desc}", normal_style),
            Paragraph("1", normal_style),
            Paragraph(f"$ {factura_data['imp_neto']:.2f}", normal_style),
            Paragraph(f"$ {factura_data['imp_neto']:.2f}", normal_style)
        ])
        
        # Si hay IVA, mostramos el detalle
        if factura_data['imp_iva'] > 0:
            data.append([
                Paragraph("", normal_style),
                Paragraph("IVA 21%", normal_style),
                Paragraph("", normal_style),
                Paragraph("", normal_style),
                Paragraph(f"$ {factura_data['imp_iva']:.2f}", normal_style)
            ])
        
        # Crear tabla
        detalle_table = Table(data, colWidths=[2*cm, 8*cm, 2*cm, 3*cm, 3*cm])
        detalle_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (4, -1), 'RIGHT'),
        ]))
        
        elements.append(detalle_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _crear_totales(self, factura_data):
        """Crea la sección de totales de la factura"""
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Datos de totales
        data = [
            ["", "", Paragraph("<b>TOTAL:</b>", normal_style), Paragraph(f"<b>$ {factura_data['imp_total']:.2f}</b>", normal_style)]
        ]
        
        # Crear tabla
        totales_table = Table(data, colWidths=[5*cm, 5*cm, 4*cm, 4*cm])
        totales_table.setStyle(TableStyle([
            ('BOX', (2, 0), (3, 0), 0.5, colors.black),
            ('BACKGROUND', (2, 0), (3, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
        ]))
        
        elements.append(totales_table)
        elements.append(Spacer(1, 10*mm))
        
        return elements
    
    def _crear_datos_cae(self, factura_data):
        """Crea la sección de datos del CAE"""
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Generar QR de AFIP
        qr_data = self._generar_datos_qr(factura_data)
        qr_image = self._generar_qr_image(qr_data)
        
        # Datos del CAE
        data = [
            [
                [
                    Paragraph("<b>CAE:</b>", normal_style),
                    Paragraph(f"{factura_data['cae']}", normal_style),
                    Spacer(1, 5*mm),
                    Paragraph("<b>Fecha Vto. CAE:</b>", normal_style),
                    Paragraph(f"{self._formatear_fecha(factura_data['fecha_vto_cae'])}", normal_style)
                ],
                qr_image
            ]
        ]
        
        # Crear tabla
        cae_table = Table(data, colWidths=[14*cm, 4*cm])
        cae_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(cae_table)
        
        return elements
    
    def _generar_datos_qr(self, factura_data):
        """
        Genera los datos para el código QR según especificación AFIP
        https://www.afip.gob.ar/fe/qr/especificaciones.asp
        """
        # Convertir el CUIT a formato sin guiones
        cuit = self.empresa['cuit'].replace('-', '')
        
        # Datos del QR
        qr_data = {
            "ver": 1,
            "fecha": self._formatear_fecha(factura_data['fecha_cbte']),
            "cuit": int(cuit),
            "ptoVta": factura_data['punto_vta'],
            "tipoCmp": factura_data['tipo_cbte'],
            "nroCmp": factura_data['numero'],
            "importe": factura_data['imp_total'],
            "moneda": "PES",
            "ctacte": 0,
            "tipoDocRec": factura_data['tipo_doc'],
            "nroDocRec": factura_data['nro_doc'],
            "tipoCodAut": 1,
            "codAut": factura_data['cae']
        }
        
        return qr_data
    
    def _generar_qr_image(self, qr_data):
        """Genera la imagen del código QR"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer)
        qr_buffer.seek(0)
        qr_image = Image(qr_buffer)
        qr_image.drawHeight = 3*cm
        qr_image.drawWidth = 3*cm
        return qr_image

