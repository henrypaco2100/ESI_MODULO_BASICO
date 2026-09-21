# ESI Calzados - Demo v13 13.0.3.2.0

## Cambio principal
Esta versión **sí carga la demo automáticamente** al instalar o al pulsar **Upgrade**.
La versión 13.0.3.1.0 solo instalaba el asistente y esperaba que el usuario pulsara
`CREAR / ACTUALIZAR DEMO`, por eso Odoo podía mostrar el módulo como instalado sin
productos, LdM ni destajos.

## Al instalar / actualizar crea
- 3 productos terminados: Bota Lona, Bota Puro Cuero y Tenis Táctico.
- Variantes por Talla y Color.
- 3 listas de materiales.
- 22 materias primas con costos y proveedor demo.
- 3 cuentas analíticas de producción.
- Categorías con costo Promedio (AVCO) y valoración automática.
- Cuenta 153000 Materias Primas.
- Cuenta 154000 Producción en Proceso.
- Cuenta 155000 Productos Terminados.
- Cuenta 215500 Destajos por Pagar.
- Diario ESIPR.
- 4 actividades de destajo.
- 3 órdenes de fabricación demo.
- 9 destajos en borrador, sin horas ni tiempos.

## Regeneración manual
Fabricación > Configuración > ESI Demo Calzados > CREAR / ACTUALIZAR DEMO.

La carga es idempotente y busca registros existentes por código/nombre/origen antes de crear.


## 13.0.3.2.1
- Compatibilidad con `esi_sd_account_v13`: completa `sd_codigo` al crear cuentas analíticas.
- La demo se carga con el botón **CREAR / ACTUALIZAR DEMO** para aislar errores de datos de la instalación del módulo.
