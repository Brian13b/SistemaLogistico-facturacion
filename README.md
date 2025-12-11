# 💰 Microservicio de Facturación Electrónica

Módulo especializado del **Sistema Logístico** encargado de la comunicación fiscal. Interactúa directamente con los Web Services SOAP de **AFIP / ARCA Argentina** para la autorización de comprobantes electrónicos (CAE).

---

## 🌟 Funcionalidades Principales
- **Emisión de Comprobantes:** Facturas A, B, Notas de Crédito y Débito.
- **Conector SOAP:** Abstracción completa del protocolo SOAP usando `Zeep`.
- **Validaciones Fiscales:** Verificación de CUITs, puntos de venta y condición tributaria.
- **Persistencia:** Historial local de comprobantes emitidos y sus CAEs.
- **Generación de PDF:** Exportación visual del comprobante.

---

## 🔧 Proceso Técnico (Flujo de Emisión)
1.  📥 **Input:** Recibe una orden de facturación (JSON) desde el Backend/Frontend.
2.  🔄 **Conversión:** Transforma los datos al formato XML requerido por WSFEv1.
3.  🔐 **Autenticación AFIP:**
    - Gestiona el Ticket de Acceso (WSAA) con Certificado y Clave Privada.
    - *Smart Caching:* Reutiliza el token si aún es válido para no saturar el servicio de AFIP.
4.  📡 **Solicitud CAE:** Envía la solicitud al WS de Facturación (WSFEv1).
5.  ✅ **Respuesta:** Recibe el CAE y fecha de vencimiento, guardándolos en PostgreSQL.
6.  🖨️ **Descarga:** Permite la descarga de la factura en formato PDF.

---

## 🛡️ Stack Tecnológico
- **Framework:** FastAPI (Python)
- **Protocolo Fiscal:** SOAP (Cliente Zeep)
- **Base de Datos:** PostgreSQL
- **Integración:** AFIP / ARCA (Entornos Homologación y Producción)

---

## 🌱 Futuras Actualizaciones
- [ ] **Envío por Email:** Envío automático de la factura PDF al cliente.
- [ ] **Cola de Tareas:** Implementar Celery/RabbitMQ para facturación masiva asíncrona.
- [ ] **Reportes Contables:** Exportación de Libros de IVA (Ventas/Compras).
- [ ] **Manejo de Errores Avanzado:** Retry automático ante caídas del servidor de AFIP.

---

## 👤 Autor
**Brian Battauz** - [GitHub](https://github.com/Brian13b)