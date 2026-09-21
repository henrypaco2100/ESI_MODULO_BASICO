# ESI Calzados v13

Complemento de **Fabricación estándar de Odoo 13** para fábricas de calzado.

## Filosofía
No reemplaza MRP. Agrega costos, faltantes, destajos, analítica y conexión contable al flujo estándar.

## Funciones
- Columnas de costo en componentes de la Orden de Fabricación.
- Costo capturado por OF para evitar que un cambio posterior del costo estándar altere el reporte histórico estimado.
- Cantidad por unidad, cantidad total, costo unitario, costo por unidad terminada y costo total.
- Disponible, faltante, costo estimado de compra y costo del faltante.
- Wizard **Preparar compra faltantes** que crea RFQ agrupadas por proveedor.
- Registro de **Destajos** sin horas ni tiempos: OF, operador, actividad, cantidad, tarifa e importe.
- Smart button Destajos desde la OF y menús de lista/formulario en Datos principales.
- Cada destajo confirmado genera asiento: **Producción en Proceso / Destajos por Pagar**.
- Los destajos confirmados se capitalizan en el costo del producto terminado usando `mrp_account.extra_cost`.
- Cuenta analítica sugerida por producto y heredada a la OF.
- Consumos de materiales llevan la cuenta analítica de la OF en la línea débito de Producción en Proceso.
- Soporta variantes estándar de Odoo (Talla, Color) y componentes de LdM aplicables a variantes.

## Valoración automática recomendada
- Materias primas: costo Promedio (AVCO) + valoración Automática.
- Producto terminado: costo Promedio (AVCO) + valoración Automática.
- Ubicación virtual Producción: cuenta de entrada/salida = Producción en Proceso.
- El módulo demo `esi_calzados_demo_v13` prepara esta configuración y crea cuentas de ejemplo si no existen.

## Reportes
Instale también `esi_produccion_report_v13` para los tres reportes:
1. Ficha de costo de producción.
2. Faltantes de materiales y costo.
3. Resumen / planilla de destajos.


## Hotfix 13.0.3.0.1
- Corregida la vista de búsqueda de destajos para Odoo 13: los filtros de Agrupar por ahora tienen `name` y `domain="[]"`.
- Se añadió `company_id` invisible al formulario de destajos para resolver correctamente el dominio de actividades por compañía.
