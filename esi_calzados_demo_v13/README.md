# ESI Calzados Demo v13

Instalar después de `esi_calzados_v13`.

Crea una demo segura, sin finalizar inventarios ni contabilizar OF automáticamente:

## Configuración contable automática
Si no existen, crea/configura estas cuentas para la compañía activa:
- 153000 Materias primas
- 154000 Producción en Proceso
- 155000 Productos terminados
- 214001 Mercaderías recibidas pendientes de facturar
- 158001 Mercaderías entregadas pendientes de facturar
- 525001 Diferencia de precio de compra
- 215500 Destajos por pagar - Producción
- 411010 Ventas de productos terminados
- 611010 Costo de productos terminados vendidos

También crea el diario `ESIPR - Valoración Producción ESI`.

La ubicación virtual **Producción** queda configurada con la cuenta 154000 como cuenta de entrada/salida de valoración.

Las categorías demo usan:
- Método de costo: **Promedio (AVCO)**.
- Valoración de inventario: **Automática**.

Flujo contable esperado al finalizar una OF:
1. Consumo materia prima: Debe 154000 Producción en Proceso / Haber 153000 Materias primas.
2. Destajo confirmado: Debe 154000 Producción en Proceso / Haber 215500 Destajos por pagar.
3. Producto terminado: Debe 155000 Productos terminados / Haber 154000 Producción en Proceso.

## 3 productos terminados
- Bota Lona ESI Demo.
- Bota Puro Cuero ESI Demo.
- Tenis Táctico ESI Demo.

Todos usan variantes estándar de Odoo de **Talla** y **Color**.
Las Bota Lona y Bota Puro Cuero incluyen suelas diferentes por talla mediante el campo estándar de Odoo **Aplicar en variantes** de la LdM.

## Destajos
Crea actividades y registros de ejemplo en borrador. No se usan tiempos ni horas.
El usuario puede confirmar los destajos desde la OF o desde Datos principales > Destajos para generar sus asientos.

## Órdenes de fabricación
Crea tres OF confirmadas de demostración. Como no crea inventario inicial artificial, el reporte de faltantes mostrará los materiales requeridos hasta que se reciban existencias reales.
