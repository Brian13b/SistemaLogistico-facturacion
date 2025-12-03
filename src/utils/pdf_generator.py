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
            'localidad': config.get('localidad', 'Paraná, Entre Ríos'),
            'cuit': config.get('cuit', ''),
            'condicion_iva': config.get('condicion_iva', 'IVA Responsable Inscripto'),
            'inicio_actividades': config.get('inicio_actividades', '01/01/2023'),
            'ingresos_brutos': config.get('ingresos_brutos', '20406953425'),
            'logo_path': config.get('logo_path', None)
        }
        
    def generar_pdf(self, factura_data):
        try:
            if not isinstance(factura_data, dict):
                factura_data = factura_data.__dict__

            if '_sa_instance_state' in factura_data:
                del factura_data['_sa_instance_state']

            tipo_letra = self._get_letra(factura_data['tipo_cbte'])
            filename = f"{tipo_letra}_{factura_data['punto_vta']:04d}_{factura_data['numero']:08d}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
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
            
            # Encabezado Principal (Empresa + Letra + Datos Factura)
            elements.extend(self._crear_encabezado_principal(factura_data, tipo_letra))
            
            # Período y Fechas
            elements.extend(self._crear_barra_periodo(factura_data))
            
            # Datos del Cliente
            elements.extend(self._crear_datos_cliente(factura_data))
            
            # Descripción
            elements.extend(self._crear_tabla_items(factura_data))
            
            # Totales y Pie
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
        styles.add(ParagraphStyle(name='LetraGrande', fontSize=28, leading=30, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='CodigoLetra', fontSize=8, leading=8, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        return styles

    def _crear_encabezado_principal(self, data, letra):
        s = self._estilos()
        tipo_nombre = self.TIPOS_COMPROBANTE.get(data['tipo_cbte'], "COMPROBANTE")
        
        # COLUMNA IZQUIERDA
        logo = self._get_logo()
        empresa_info = [
            logo if logo else Spacer(1, 1),
            Paragraph(f"<b>{self.empresa['razon_social']}</b>", s['Heading3']),
            Spacer(1, 2),
            Paragraph(f"<b>Domicilio Comercial:</b> {self.empresa['domicilio']}", s['Small']),
            Paragraph(f"<b>Condición frente al IVA:</b> {self.empresa['condicion_iva']}", s['Small']),
        ]

        # COLUMNA CENTRAL
        cuadro_letra = Table([
            [Paragraph(letra, s['LetraGrande'])],
            [Paragraph(f"COD. {data['tipo_cbte']:02d}", s['CodigoLetra'])]
        ], colWidths=[1.5*cm], rowHeights=[1.0*cm, 0.5*cm])
        cuadro_letra.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))

        # COLUMNA DERECHA
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

        tabla_header = Table([
            [empresa_info, cuadro_letra, factura_info]
        ], colWidths=[8*cm, 2*cm, 9*cm])
        
        tabla_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEAFTER', (0,0), (0,0), 0.5, colors.black),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('LEFTPADDING', (2,0), (2,0), 10),
        ]))

        return [tabla_header, Spacer(1, 0.2*cm)]

    def _crear_barra_periodo(self, data):
        s = self._estilos()
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
            Paragraph(f"<b>Apellido y Nombre / Razón Social:</b> Empresa Ficticia S.A.", s['Small']), 
        ]
        # Fila 2
        r2 = [
            Paragraph(f"<b>Condición frente al IVA:</b> {cond_iva_txt}", s['Small']),
            Paragraph(f"<b>Domicilio:</b> Av. Ficticia 123, Paraná, Entre Ríos", s['Small']),
        ]
        # Fila 3
        r3 = [
            Paragraph(f"<b>Condición de venta:</b> Contado", s['Small']),
            ""
        ]

        t = Table([r1, r2, r3], colWidths=[6*cm, 13*cm])
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 4),
            ('SPAN', (1,2), (1,2)) 
        ]))
        return [t, Spacer(1, 0.5*cm)]

    def _crear_tabla_items(self, data):
        s = self._estilos()
        
        # Encabezados exactos del modelo
        headers = [
            "Código", "Producto / Servicio", "Cantidad", "U. Medida", 
            "Precio Unit.", "% Bonif.", "Subtotal", "Alicuota IVA", "Subtotal c/IVA"
        ]
        header_row = [Paragraph(f"<b>{h}</b>", s['CenterBold']) for h in headers]

        neto = float(data['imp_neto'])
        descripcion = data.get('descripcion') or "Servicios logísticos"
        cantidad = float(data.get('cantidad', 1.0))
        precio_unit = float(data.get('precio_unitario', data['imp_neto']))
        unidad = str(data.get('unidad_medida') or 'Unidad')
        alicuota = float(data.get('alicuota_iva', 21.0))

        subtotal_neto = cantidad * precio_unit
        monto_iva = subtotal_neto * (alicuota / 100)
        subtotal_final = subtotal_neto + monto_iva
        
        # Fila de datos
        item_row = [
            Paragraph("", s['Small']),                          # Código
            Paragraph(descripcion, s['Small']),                 # Descripción
            Paragraph(f"{cantidad:.2f}", s['Right']),           # Cantidad
            Paragraph(unidad, s['Small']),                      # U. Medida
            Paragraph(f"{precio_unit:,.2f}", s['Right']),       # Precio Unit.
            Paragraph("0,00", s['Right']),                      # % Bonif.
            Paragraph(f"{subtotal_neto:,.2f}", s['Right']),     # Subtotal
            Paragraph(f"{alicuota:.2f}%", s['Right']),          # Alicuota IVA
            Paragraph(f"{subtotal_final:,.2f}", s['Right']),    # Subtotal c/IVA
        ]

        rows = [header_row, item_row]
        
        widths = [1.2*cm, 5.5*cm, 1.5*cm, 1.8*cm, 2.0*cm, 1.5*cm, 2.0*cm, 1.5*cm, 2.0*cm]
        
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'), 
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        
        return [t, Spacer(1, 0.2*cm)]

    def _crear_totales_y_pie(self, data):
        s = self._estilos()
        
        neto = float(data['imp_neto'])
        iva = float(data['imp_iva'])
        trib = float(data.get('imp_trib', 0))
        total = float(data['imp_total'])
        
        rows = []
        rows.append(["Subtotal:", f"$ {neto:,.2f}"])
        
        if data['tipo_cbte'] in [1, 2, 3]:
             rows.append(["IVA Inscripto:", f"$ {iva:,.2f}"])
        
        if trib > 0:
            rows.append(["Importe Otros Tributos:", f"$ {trib:,.2f}"])
            
        rows.append([Paragraph("<b>Importe Total:</b>", s['BoldSmall']), Paragraph(f"<b>$ {total:,.2f}</b>", s['BoldSmall'])])
        
        # QR y CAE
        qr_img = self._generar_qr(data)
        cae_text = [
            Paragraph(f"<b>CAE N°: {data['cae']}</b>", s['BoldSmall']),
            Paragraph(f"<b>Fecha de Vto. de CAE: {self._format_date(data['fecha_vto_cae'])}</b>", s['BoldSmall']),
        ]
        
        left_content = Table([[qr_img, cae_text]], colWidths=[3.5*cm, 6*cm])
        left_content.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

        # Tabla derecha
        right_content = Table(rows, colWidths=[4*cm, 3*cm])
        right_content.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'), 
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BACKGROUND', (-2,-1), (-1,-1), colors.lightgrey), 
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