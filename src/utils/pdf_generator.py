#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generador de PDF para las facturas electrónicas de AFIP
Estilo estándar RG 1415
"""

import os
import logging
import json
import qrcode
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing

logger = logging.getLogger('facturacion_afip.pdf')

class FacturaPDF:
    """Generador de PDF con diseño estándar AFIP"""
    
    TIPOS_COMPROBANTE = {
        1: "FACTURA A", 6: "FACTURA B", 11: "FACTURA C",
        2: "NOTA DE DÉBITO A", 7: "NOTA DE DÉBITO B", 12: "NOTA DE DÉBITO C",
        3: "NOTA DE CRÉDITO A", 8: "NOTA DE CRÉDITO B", 13: "NOTA DE CRÉDITO C"
    }
    
    TIPOS_DOCUMENTO = {
        80: "CUIT", 86: "CUIL", 96: "DNI", 99: "Doc. Final"
    }

    CONDICIONES_IVA = {
        1: "IVA Responsable Inscripto",
        4: "IVA Sujeto Exento",
        5: "Consumidor Final",
        6: "Responsable Monotributo",
        13: "Monotributista Social"
    }

    def __init__(self, config):
        self.config = config
        self.output_dir = config.get('pdf_output_dir', '/tmp')
        
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except OSError:
                self.output_dir = '/tmp'
            
        self.empresa = {
            'razon_social': config.get('razon_social', 'MI EMPRESA S.A.'),
            'domicilio': config.get('domicilio', 'Domicilio Fiscal Desconocido'),
            'localidad': config.get('localidad', ''),
            'cuit': config.get('cuit', ''),
            'condicion_iva': config.get('condicion_iva', 'IVA Responsable Inscripto'),
            'inicio_actividades': config.get('inicio_actividades', '-'),
            'ingresos_brutos': config.get('ingresos_brutos', '-'),
            'logo_path': config.get('logo_path', None)
        }
        
    def generar_pdf(self, factura_data):
        try:
            if not isinstance(factura_data, dict):
                factura_data = factura_data.__dict__

            # Limpieza de objeto SQLAlchemy
            if '_sa_instance_state' in factura_data:
                del factura_data['_sa_instance_state']

            tipo_letra = self._get_letra(factura_data['tipo_cbte'])
            filename = f"{tipo_letra}_{factura_data['punto_vta']:04d}_{factura_data['numero']:08d}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            # Márgenes estrechos para aprovechar la hoja A4
            doc = SimpleDocTemplate(
                output_path, 
                pagesize=A4, 
                leftMargin=1*cm, 
                rightMargin=1*cm, 
                topMargin=1*cm, 
                bottomMargin=1*cm
            )
            
            self.factura_actual = factura_data
            elements = []
            
            # 1. Encabezado Principal (Empresa + Letra + Datos Factura)
            elements.extend(self._crear_encabezado_principal(factura_data, tipo_letra))
            
            # 2. Período y Fechas
            elements.extend(self._crear_barra_periodo(factura_data))
            
            # 3. Datos del Cliente
            elements.extend(self._crear_datos_cliente(factura_data))
            
            # 4. Tabla de Items
            elements.extend(self._crear_tabla_items(factura_data))
            
            # 5. Totales y Pie
            elements.extend(self._crear_totales_y_pie(factura_data))
            
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

    def _format_date(self, date_str):
        if not date_str: return "-"
        try:
            d = str(date_str).strip()
            if len(d) == 8 and d.isdigit(): 
                return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
            if "-" in d: 
                return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
            return d
        except: return str(date_str)

    def _estilos(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10))
        styles.add(ParagraphStyle(name='BoldSmall', fontSize=8, leading=10, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='CenterBold', fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='Right', fontSize=9, alignment=TA_RIGHT))
        styles.add(ParagraphStyle(name='LetraGrande', fontSize=28, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='CodigoLetra', fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        return styles

    def _crear_encabezado_principal(self, data, letra):
        s = self._estilos()
        tipo_nombre = self.TIPOS_COMPROBANTE.get(data['tipo_cbte'], "COMPROBANTE")
        
        # --- COLUMNA IZQUIERDA (EMPRESA) ---
        logo = self._get_logo()
        empresa_info = [
            logo if logo else Spacer(1, 1),
            Paragraph(f"<b>{self.empresa['razon_social']}</b>", s['Heading3']),
            Spacer(1, 2),
            Paragraph(f"<b>Domicilio Comercial:</b> {self.empresa['domicilio']}", s['Small']),
            Paragraph(f"<b>Condición frente al IVA:</b> {self.empresa['condicion_iva']}", s['Small']),
        ]

        # --- COLUMNA CENTRAL (LETRA) ---
        # Cuadro con la letra A/B/C y el código
        cuadro_letra = Table([
            [Paragraph(letra, s['LetraGrande'])],
            [Paragraph(f"COD. {data['tipo_cbte']:02d}", s['CodigoLetra'])]
        ], colWidths=[1.5*cm])
        cuadro_letra.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))

        # --- COLUMNA DERECHA (DATOS FACTURA) ---
        factura_info = [
            Paragraph(f"<b>{tipo_nombre}</b>", s['Heading3']),
            Spacer(1, 5),
            Paragraph(f"<b>Punto de Venta: {data['punto_vta']:04d}   Comp. Nro: {data['numero']:08d}</b>", s['BodyText']),
            Paragraph(f"<b>Fecha de Emisión:</b> {self._format_date(data['fecha_cbte'])}", s['BodyText']),
            Spacer(1, 5),
            Paragraph(f"<b>CUIT:</b> {self.empresa['cuit']}", s['Small']),
            Paragraph(f"<b>Ingresos Brutos:</b> {self.empresa['ingresos_brutos']}", s['Small']),
            Paragraph(f"<b>Inicio de Actividades:</b> {self.empresa['inicio_actividades']}", s['Small']),
        ]

        # Tabla Maestra del Encabezado (2 columnas + letra flotante visualmente)
        # Simulamos la linea divisoria con un borde derecho en la primera celda
        tabla_header = Table([
            [empresa_info, cuadro_letra, factura_info]
        ], colWidths=[8*cm, 2*cm, 9*cm])
        
        tabla_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEAFTER', (0,0), (0,0), 0.5, colors.black), # Línea vertical al medio (técnicamente a la derecha de col 1)
            ('ALIGN', (1,0), (1,0), 'CENTER'), # Letra centrada
            ('LEFTPADDING', (2,0), (2,0), 10), # Margen para la col derecha
        ]))

        return [tabla_header, Spacer(1, 0.2*cm)]

    def _crear_barra_periodo(self, data):
        s = self._estilos()
        # Fechas de servicio (si existen)
        f_desde = self._format_date(data.get('fecha_serv_desde') or data['fecha_cbte'])
        f_hasta = self._format_date(data.get('fecha_serv_hasta') or data['fecha_cbte'])
        f_vto = self._format_date(data.get('fecha_vto_pago') or data['fecha_cbte'])

        row = [
            Paragraph(f"<b>Período Facturado Desde:</b> {f_desde}", s['Small']),
            Paragraph(f"<b>Hasta:</b> {f_hasta}", s['Small']),
            Paragraph(f"<b>Fecha de Vto. para el pago:</b> {f_vto}", s['Small'])
        ]
        
        t = Table([row], colWidths=[6.3*cm, 6.3*cm, 6.4*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        return [t, Spacer(1, 0.2*cm)]

    def _crear_datos_cliente(self, data):
        s = self._estilos()
        
        cond_iva_id = data.get('condicion_iva_receptor_id')
        cond_iva_txt = self.CONDICIONES_IVA.get(cond_iva_id, "Consumidor Final")
        doc_tipo = self.TIPOS_DOCUMENTO.get(data['tipo_doc'], str(data['tipo_doc']))
        
        # Fila 1
        r1 = [
            Paragraph(f"<b>{doc_tipo}:</b> {data['nro_doc']}", s['Small']),
            Paragraph(f"<b>Apellido y Nombre / Razón Social:</b> -", s['Small']), # Nombre no guardado en este modelo simplificado
        ]
        # Fila 2
        r2 = [
            Paragraph(f"<b>Condición frente al IVA:</b> {cond_iva_txt}", s['Small']),
            Paragraph(f"<b>Domicilio:</b> -", s['Small']),
        ]
        # Fila 3
        r3 = [
            Paragraph(f"<b>Condición de venta:</b> Contado", s['Small']),
            ""
        ]

        t = Table([r1, r2, r3], colWidths=[6*cm, 13*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            #('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
            ('SPAN', (1,2), (1,2)) # Span para la última celda vacía
        ]))
        return [t, Spacer(1, 0.5*cm)]

    def _crear_tabla_items(self, data):
        s = self._estilos()
        
        # Encabezados exactos del modelo
        headers = [
            "Código", "Producto / Servicio", "Cantidad", "U. Medida", 
            "Precio Unit.", "% Bonif.", "Imp. Bonif.", "Subtotal"
        ]
        header_row = [Paragraph(f"<b>{h}</b>", s['CenterBold']) for h in headers]

        # Construcción de la fila del ítem (Simulada desde totales ya que no guardamos ítems individuales)
        neto = float(data['imp_neto'])
        concepto_map = {1: "Productos", 2: "Servicios", 3: "Productos y Servicios"}
        descripcion = data.get('descripcion') or f"Facturación por {concepto_map.get(data['concepto'], '')}"
        
        # Fila de datos
        item_row = [
            Paragraph("001", s['Small']),               # Código
            Paragraph(descripcion, s['Small']),         # Descripción
            Paragraph("1,00", s['Right']),              # Cantidad
            Paragraph("Unidad", s['Small']),            # U. Medida
            Paragraph(f"{neto:,.2f}", s['Right']),      # Precio Unit.
            Paragraph("0,00", s['Right']),              # % Bonif.
            Paragraph("0,00", s['Right']),              # Imp. Bonif.
            Paragraph(f"{neto:,.2f}", s['Right'])       # Subtotal
        ]

        # Generar filas vacías para llenar espacio si se desea, aquí solo 1
        rows = [header_row, item_row]

        # Definir anchos de columna (ajustados al ancho A4)
        # Total disponible ~19cm
        widths = [1.5*cm, 6*cm, 1.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm]
        
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), # Fondo encabezado
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'), # Descripción a la izquierda
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        
        return [t, Spacer(1, 0.2*cm)]

    def _crear_totales_y_pie(self, data):
        s = self._estilos()
        
        # --- TABLA DE TOTALES (Alineada a la derecha) ---
        # Filas: Subtotal, Otros Tributos, Total
        neto = float(data['imp_neto'])
        iva = float(data['imp_iva'])
        trib = float(data.get('imp_trib', 0))
        total = float(data['imp_total'])
        
        rows = []
        rows.append(["Subtotal:", f"$ {neto:,.2f}"])
        
        # Detalle IVA (Solo si es A)
        if data['tipo_cbte'] in [1, 2, 3]:
             rows.append(["IVA Inscripto:", f"$ {iva:,.2f}"])
        
        if trib > 0:
            rows.append(["Importe Otros Tributos:", f"$ {trib:,.2f}"])
            
        rows.append([Paragraph("<b>Importe Total:</b>", s['BoldSmall']), Paragraph(f"<b>$ {total:,.2f}</b>", s['BoldSmall'])])
        
        # Tabla de totales flota a la derecha
        # Usamos una tabla contenedora: Izquierda (QR/CAE) - Derecha (Totales)
        
        # IZQUIERDA: QR y CAE
        qr_img = self._generar_qr(data)
        cae_text = [
            Paragraph(f"<b>CAE N°: {data['cae']}</b>", s['BoldSmall']),
            Paragraph(f"<b>Fecha de Vto. de CAE: {self._format_date(data['fecha_vto_cae'])}</b>", s['BoldSmall']),
        ]
        
        # Si hay logo de AFIP se pondría aquí, usaremos el QR y texto
        left_content = Table([[qr_img, cae_text]], colWidths=[3.5*cm, 6*cm])
        left_content.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

        # DERECHA: Tabla de números
        right_content = Table(rows, colWidths=[4*cm, 3*cm])
        right_content.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'), # Negrita al total
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (-2,-1), (-1,-1), colors.lightgrey), # Fondo al total
        ]))

        # Tabla Contenedora del Pie
        main_footer = Table([[left_content, right_content]], colWidths=[11*cm, 8*cm])
        main_footer.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))

        return [Spacer(1, 0.5*cm), main_footer]

    def _generar_qr(self, data):
        try:
            cuit = self.empresa['cuit'].replace("-", "")
            qr_dict = {
                "ver": 1,
                "fecha": data['fecha_cbte'],
                "cuit": int(cuit) if cuit.isdigit() else 0,
                "ptoVta": data['punto_vta'],
                "tipoCmp": data['tipo_cbte'],
                "nroCmp": data['numero'],
                "importe": float(data['imp_total']),
                "moneda": "PES",
                "ctz": float(data['moneda_cotiz']),
                "tipoDocRec": data['tipo_doc'],
                "nroDocRec": int(data['nro_doc']) if str(data['nro_doc']).isdigit() else 0,
                "tipoCodAut": "E",
                "codAut": int(data['cae']) if str(data['cae']).isdigit() else 0
            }
            
            qr_str = json.dumps(qr_dict)
            import base64
            qr_b64 = base64.b64encode(qr_str.encode()).decode()
            url_qr = f"https://www.afip.gob.ar/fe/qr/?p={qr_b64}"
            
            qr = qrcode.make(url_qr)
            img_buffer = BytesIO()
            qr.save(img_buffer)
            img_buffer.seek(0)
            return Image(img_buffer, width=3*cm, height=3*cm)
        except Exception as e:
            logger.error(f"Error generando QR: {e}")
            return Spacer(1,1)

    def _get_logo(self):
        if self.empresa['logo_path'] and os.path.exists(self.empresa['logo_path']):
            return Image(self.empresa['logo_path'], width=4*cm, height=2*cm)
        return None