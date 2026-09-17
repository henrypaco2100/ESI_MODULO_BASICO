# ESI MODULO BASICO - Odoo 13 - Versión de prueba

## Cambios principales

- Se conservan los nombres técnicos de los addons para evitar romper XML IDs y dependencias.
- Marca visible, autor, mantenedor e iconos actualizados a ESI - Especialistas en Sistemas Integrados.
- `bi_automated_sale_order` y `bi_automated_purchase_order` ya no dependen de Multi Store.
- Se añadieron integraciones opcionales y auto-instalables:
  - `automated_sale_multi_store`
  - `automated_purchase_multi_store`
- Tipo de Ventas / Tipo de Compras conservan almacén, secuencias, compañía y diarios.
- Nuevos booleanos:
  - Validar Entrega / Validar Recepción.
  - Publicar Factura.
- Al confirmar una venta/compra, Automated intenta crear la factura respetando las políticas estándar de facturación de Odoo.
- Si el booleano de entrega/recepción está activo, intenta validar la transferencia. Los productos con lote/serie se dejan pendientes para completar manualmente.
- No se modifica `date_done`, `stock.move.date`, fechas contables ni `stock.valuation.layer.create_date` desde Automated.
- Se eliminó la sobreescritura activa de `_compute_scheduled_date` de `sd_stock_v13`.
- El módulo histórico `sd_stock_valuation_layer` se conserva por nombre técnico, pero está temporalmente `installable=False` y `auto_install=False`.
- `sd_ocultar_campos_botones` se conserva por compatibilidad de nombre técnico, pero ya no carga vistas que oculten botones estándar.
- Los informes ESI de Ventas y Compras dependen de sus Automated y quedan en auto instalación.

## Nuevo pago desde Venta / Compra

Se añadió un wizard ESI propio desde `sale.order` y `purchase.order`.

El usuario comercial no necesita pertenecer a grupos contables. El wizard valida en servidor que:

1. el usuario tenga acceso a la venta/compra;
2. la factura pertenezca realmente a ese documento;
3. la factura esté publicada y con saldo pendiente;
4. el importe no supere el saldo pendiente;
5. el diario utilizado sea exactamente el configurado en el Tipo de Venta/Compra;
6. la compañía coincida.

Solo después de esas validaciones, la creación/publicación del `account.payment` se ejecuta con `sudo()`.
Se guarda además el usuario real que solicitó el pago en campos de auditoría ESI del pago.

## Prueba recomendada

1. Hacer copia de la base de pruebas.
2. Copiar todos los addons del paquete a sus rutas de addons.
3. Reiniciar Odoo y actualizar la lista de aplicaciones.
4. Actualizar/instalar primero Store si se utilizará Multi Store.
5. Instalar/actualizar `bi_automated_sale_order` y `bi_automated_purchase_order`.
6. Verificar que los puentes Store se auto-instalen si Store está presente.
7. Crear un Tipo de Venta y un Tipo de Compra con sus secuencias, almacén y diarios.
8. Probar una venta con Validar Entrega activado y otra desactivado.
9. Probar Publicar Factura activado/desactivado.
10. Con factura publicada, probar pago total y pago parcial desde el pedido.
11. Repetir el mismo flujo en Compras.

## Nota

Esta versión pasó validación estática de Python, XML, manifests y archivos declarados. La prueba final debe hacerse dentro de una base Odoo 13 real, porque los flujos pueden variar según módulos locales instalados, reglas contables, lotes/series y configuración de productos.
