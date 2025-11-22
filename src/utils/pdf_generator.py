#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import qrcode
import json
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

logger = logging.getLogger('facturacion_afip.pdf')

class FacturaPDF:
    """Generador de PDF actualizado para ARCA v4.1"""
    
    TIPOS_COMPROBANTE = {
        1: "FACTURA A", 6: "FACTURA B", 11: "FACTURA C",
        2: "NOTA DE DÉBITO A", 7: "NOTA DE DÉBITO B", 12: "NOTA DE DÉBITO C",
        3: "NOTA DE CRÉDITO A", 8: "NOTA DE CRÉDITO B", 13: "NOTA DE CRÉDITO C"
    }
    
    TIPOS_DOCUMENTO = {
        80: "CUIT", 86: "CUIL", 96: "DNI", 99: "Doc. Final"
    }

    # Mapeo de condiciones de IVA (ARCA)
    CONDICIONES_IVA = {
        1: "IVA Responsable Inscripto",
        4: "IVA Sujeto Exento",
        5: "Consumidor Final",
        6: "Responsable Monotributo",
        13: "Monotributista Social"
    }

    def __init__(self, config):
        self.config = config
        self.output_dir = config.get('pdf_output_dir', 'facturas_pdf')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.empresa = {
            'razon_social': config.get('razon_social', 'MI EMPRESA S.A.'),
            'domicilio': config.get('domicilio', 'Domicilio Fiscal'),
            'localidad': config.get('localidad', 'Ciudad'),
            'cuit': config.get('cuit', ''),
            'condicion_iva': config.get('condicion_iva', 'IVA Responsable Inscripto'),
            'inicio_actividades': config.get('inicio_actividades', '-'),
            'logo_path': config.get('logo_path', None)
        }
        
    def generar_pdf(self, factura_data):
        try:
            # Convertir objeto SQLAlchemy a dict si es necesario
            if not isinstance(factura_data, dict):
                factura_data = factura_data.__dict__

            tipo_letra = self._get_letra(factura_data['tipo_cbte'])
            filename = f"{tipo_letra}_{factura_data['punto_vta']:04d}_{factura_data['numero']:08d}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            doc = SimpleDocTemplate(output_path, pagesize=A4, margin=(1*cm, 1*cm, 1*cm, 1*cm))
            elements = []
            
            self.factura_actual = factura_data
            
            elements.extend(self._crear_encabezado(factura_data, tipo_letra))
            elements.extend(self._crear_datos_cliente(factura_data))
            elements.extend(self._crear_detalles_factura(factura_data))
            elements.extend(self._crear_totales(factura_data))
            elements.extend(self._crear_cae_qr(factura_data))
            
            doc.build(elements, onFirstPage=self._agregar_metadata)
            return output_path
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            raise

    def _get_letra(self, tipo):
        if tipo in [1, 2, 3]: return "A"
        if tipo in [6, 7, 8]: return "B"
        if tipo in [11, 12, 13]: return "C"
        return "X"

    def _agregar_metadata(self, canvas, doc):
        canvas.setTitle(f"Factura {self.factura_actual.get('numero')}")
        canvas.setAuthor(self.empresa['razon_social'])

    def _crear_encabezado(self, data, letra):
        styles = getSampleStyleSheet()
        tipo_nombre = self.TIPOS_COMPROBANTE.get(data['tipo_cbte'], "COMPROBANTE")
        
        # Tabla superior
        logo = self._get_logo()
        
        # Columna Central (Letra)
        col_letra = [
            Paragraph(f"<b>{letra}</b>", ParagraphStyle('Letra', fontSize=36, alignment=1, spaceAfter=10)),
            Paragraph(f"Cod. {data['tipo_cbte']:02d}", ParagraphStyle('Cod', fontSize=9, alignment=1))
        ]

        # Columna Derecha (Datos Factura)
        fecha = self._format_date(data['fecha_cbte'])
        col_dat = [
            Paragraph(f"<b>{tipo_nombre}</b>", styles['Heading3']),
            Paragraph(f"<b>N° {data['punto_vta']:04d}-{data['numero']:08d}</b>", styles['Heading4']),
            Spacer(1, 5),
            Paragraph(f"Fecha: {fecha}", styles['Normal']),
            Paragraph(f"CUIT: {self.empresa['cuit']}", styles['Normal']),
            Paragraph(f"Ing. Brutos: {self.empresa.get('ingresos_brutos','-')}", styles['Normal']),
            Paragraph(f"Ini. Actividades: {self.empresa['inicio_actividades']}", styles['Normal']),
        ]

        # Columna Izquierda (Empresa)
        col_emp = [
            logo if logo else Spacer(1,1),
            Paragraph(f"<b>{self.empresa['razon_social']}</b>", styles['Heading3']),
            Paragraph(self.empresa['domicilio'], styles['Normal']),
            Paragraph(f"{self.empresa['localidad']}", styles['Normal']),
            Paragraph(f"<b>{self.empresa['condicion_iva']}</b>", styles['Normal']),
        ]

        table = Table([[col_emp, col_letra, col_dat]], colWidths=[7*cm, 3*cm, 9*cm])
        table.setStyle(TableStyle([
            ('BOX', (1,0), (1,0), 1, colors.black), # Cuadro letra
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
        return [table, Spacer(1, 0.5*cm)]

    def _crear_datos_cliente(self, data):
        styles = getSampleStyleSheet()
        
        # Obtener descripción de condición IVA del receptor (ARCA)
        cond_iva_id = data.get('condicion_iva_receptor_id')
        cond_iva_txt = self.CONDICIONES_IVA.get(cond_iva_id, "Consumidor Final")
        
        doc_tipo = self.TIPOS_DOCUMENTO.get(data['tipo_doc'], str(data['tipo_doc']))
        
        rows = [
            [Paragraph(f"<b>Cliente:</b> Doc. {doc_tipo}: {data['nro_doc']}", styles['Normal'])],
            [Paragraph(f"<b>Condición IVA:</b> {cond_iva_txt}", styles['Normal'])],
            [Paragraph(f"<b>Domicilio:</b> -", styles['Normal'])] # Podrías agregarlo al modelo si lo tienes
        ]
        
        t = Table(rows, colWidths=[19*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return [t, Spacer(1, 0.5*cm)]

    def _crear_detalles_factura(self, data):
        styles = getSampleStyleSheet()
        header = [
            Paragraph("<b>Concepto</b>", styles['Normal']),
            Paragraph("<b>Subtotal</b>", styles['Normal'])
        ]
        
        # Convertir Decimal a float para formateo
        neto = float(data['imp_neto'])
        rows = [header]
        
        # Fila genérica (ya que no guardamos items individuales en este modelo simplificado)
        concepto_map = {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}
        descripcion = data.get('descripcion') or f"Facturación por {concepto_map.get(data['concepto'], '')}"

        rows.append([
            Paragraph(descripcion, styles['Normal']),
            Paragraph(f"$ {neto:,.2f}", styles['Normal'])
        ])
        
        t = Table(rows, colWidths=[15*cm, 4*cm])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return [t, Spacer(1, 0.5*cm)]

    def _crear_totales(self, data):
        styles = getSampleStyleSheet()
        style_right = ParagraphStyle('Right', parent=styles['Normal'], alignment=2)
        
        rows = []
        rows.append(["Subtotal Neto:", f"$ {float(data['imp_neto']):,.2f}"])
        
        # Desglosar IVA si existe
        if data.get('detalles_iva'):
            ivas = json.loads(data['detalles_iva']) if isinstance(data['detalles_iva'], str) else data['detalles_iva']
            for iv in ivas:
                # Mapeo ID AFIP a texto
                tasa = {5: "21%", 4: "10.5%", 6: "27%"}.get(iv['Id'], str(iv['Id']))
                rows.append([f"IVA {tasa}:", f"$ {float(iv['Importe']):,.2f}"])
        
        if float(data.get('imp_trib', 0)) > 0:
            rows.append(["Tributos:", f"$ {float(data['imp_trib']):,.2f}"])
            
        rows.append([Paragraph("<b>TOTAL:</b>", style_right), Paragraph(f"<b>$ {float(data['imp_total']):,.2f}</b>", style_right)])
        
        t = Table(rows, colWidths=[15*cm, 4*cm])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return [t, Spacer(1, 1*cm)]

    def _crear_cae_qr(self, data):
        styles = getSampleStyleSheet()
        
        # Texto CAE
        cae_info = [
            Paragraph(f"<b>CAE: {data['cae']}</b>", styles['Normal']),
            Paragraph(f"<b>Vencimiento CAE: {self._format_date(data['fecha_vto_cae'])}</b>", styles['Normal'])
        ]
        
        # Generar QR
        qr_img = self._generar_qr(data)
        
        t = Table([[cae_info, qr_img]], colWidths=[14*cm, 5*cm])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        return [t]

    def _generar_qr(self, data):
        # Datos requeridos por AFIP para QR
        qr_dict = {
            "ver": 1,
            "fecha": data['fecha_cbte'],
            "cuit": int(self.empresa['cuit'].replace("-", "")),
            "ptoVta": data['punto_vta'],
            "tipoCmp": data['tipo_cbte'],
            "nroCmp": data['numero'],
            "importe": float(data['imp_total']),
            "moneda": data['moneda'],
            "ctz": float(data['moneda_cotiz']),
            "tipoDocRec": data['tipo_doc'],
            "nroDocRec": int(data['nro_doc']),
            "tipoCodAut": "E", # E para CAE
            "codAut": int(data['cae'])
        }
        
        qr_str = json.dumps(qr_dict)
        # Codificar en base64 como pide AFIP
        qr_b64 = base64.b64encode(qr_str.encode()).decode()
        url_qr = f"https://www.afip.gob.ar/fe/qr/?p={qr_b64}"
        
        qr = qrcode.make(url_qr)
        img_buffer = BytesIO()
        qr.save(img_buffer)
        img_buffer.seek(0)
        return Image(img_buffer, width=3*cm, height=3*cm)

    def _get_logo(self):
        if self.empresa['logo_path'] and os.path.exists(self.empresa['logo_path']):
            return Image(self.empresa['logo_path'], width=4*cm, height=2*cm)
        return None

    def _format_date(self, date_str):
        if not date_str: return "-"
        try:
            return datetime.strptime(str(date_str), "%Y%m%d").strftime("%d/%m/%Y")
        except: return date_str