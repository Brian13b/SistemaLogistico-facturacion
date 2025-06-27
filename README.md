# 💰 Módulo de facturación electrónica del sistema de gestión de flotas.

Este repositorio forma parte del **Sistema Logistico** y se encarga de la gestión de la facturación electrónica. Está integrado con el **web service SOAP** de **AFIP / ARCA Argentina** para emitir comprobantes fiscales válidos, automatizando parte del proceso tributario.

---

🌟 **¿Qué hace este módulo?**  
- Permite generar facturas electrónicas válidas ante AFIP, utilizando el servicio ARCA.  
- Gestiona la conexión al servicio SOAP para autorizar y validar comprobantes.  
- Proporciona una API REST para que el frontend pueda crear, consultar y descargar facturas.  
- Administra los datos de facturación relacionados con viajes y servicios.

---

🔧 **Características principales**  
- 📄 Emisión de facturas electrónicas tipo A, B y otros comprobantes autorizados.  
- 🔐 Validación automática de CUIT, condición fiscal y puntos de venta.  
- 📤 Conexión directa al web service **SOAP** de **AFIP/ARCA Argentina**.  
- 🌐 API REST para consulta y gestión desde el frontend.  
- 🗃️ Registro de facturas emitidas con historial y estado (CAE, vencimiento, etc.).

---

📚 **Flujo de trabajo**  
1. 📦 Se genera una orden de facturación vinculada a un viaje.  
2. 🔄 Se conecta al web service SOAP de AFIP a través de ARCA para emitir el comprobante.  
3. 🧾 Recibe el CAE y demás datos fiscales.  
4. 💾 Guarda la factura en la base de datos y la expone para consulta o descarga.  
5. 🖨️ Permite la exportación o visualización de la factura en formato PDF.

---

📚 **Proceso técnico**  
1. 📝 Usuario completa un formulario desde el frontend.  
2. 📡 Solicitud enviada al backend vía API.  
3. 🔄 Conexión al web service SOAP de AFIP para emitir la factura.  
4. ✅ Recepción del CAE (Código de Autorización Electrónica).  
5. 💾 Registro de la factura en la base de datos.  
6. 📤 Exposición de la factura al frontend para visualización o descarga.

---

🛡️ **Tecnologías Usadas**  
- 🖥️ Lenguaje: Python  
- ⚡ Framework: FastAPI 
- 🔗 Integración SOAP: Zeep / Suds / librería equivalente  
- 💼 Servicio fiscal: AFIP / ARCA Argentina (SOAP)  
- 🗄️ Base de datos: PostgreSQL

---

🌱 **Futuras actualizaciones**  
- 📈 Reportes fiscales automáticos por mes/año.  
- ✉️ Envío de facturas por correo electrónico.  
- 💳 Integración con pasarelas de pago para facturación inmediata.

---
