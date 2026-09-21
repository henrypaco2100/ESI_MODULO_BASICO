# ESI Demo Farmacia v13

Módulo de demostración integral para el paquete básico ESI en Odoo 13.

## Qué crea

- Plan contable básico orientativo para Bolivia.
- Balance General y Estado de Resultados en `account.financial.report`, ordenados con el asa de arrastre de Odoo.
  El campo técnico `sequence` queda oculto al usuario y controla el mismo orden en pantalla, PDF y Excel.
- Dos sucursales: **Central** y **Sucursal Montero**.
- Dos almacenes asociados a las sucursales.
- Cuatro secuencias ESI: Venta Central, Venta Montero, Compra Central y Compra Montero.
  Los dos tipos de cada sucursal comparten la secuencia de su operación para mantener una numeración continua por sucursal.
- Dos Tipos de Venta por sucursal: **Venta Inmediata** y **Venta por Entregar**.
- Dos Tipos de Compra por sucursal: **Compra Inmediata** y **Compra Importación**.
- 20 productos de farmacia en categorías con **Costo Promedio (AVCO)** y **Valoración Automática**.
- Dos puntos de venta: **POS Central** y **POS Montero**.
- 4 compras y 4 ventas confirmadas para ejercitar ambos flujos.

## Comportamiento de los flujos

- Venta Inmediata: valida entrega y publica factura.
- Venta por Entregar: confirma venta y publica factura, dejando la entrega pendiente.
- Compra Inmediata: valida recepción y publica factura de proveedor.
- Compra Importación: confirma compra y publica factura, dejando la recepción pendiente.

## Importante

Este módulo se diseñó únicamente para una **base de pruebas**. No instalar en producción.
No utiliza el antiguo reproceso de valoración. La valoración automática se realiza con la lógica estándar de Odoo 13.
