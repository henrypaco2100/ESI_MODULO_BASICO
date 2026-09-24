# ESI Calzados - Complemento MRP v13

Complementa Fabricación estándar de Odoo 13; no reemplaza MRP.

## Novedades 13.0.4.0.0

- **Grupos de órdenes de producción** en Fabricación > Operaciones.
- Un grupo puede contener varias variantes de calzado (modelo, talla, color) y genera una OF por línea.
- Campos del grupo: fuente/origen, pedido de venta, cliente, vendedor y **encargado de producción obligatorio**.
- Smart buttons para ver **Producciones**, **Materiales consolidados** y **LdM**.
- Control de LdM por línea: permite crear/editar la Lista de Materiales y bloquea la creación de OF si falta una LdM válida.
- Resumen de costos del grupo: materiales, faltantes, otros costos y total estimado.
- Desde Ventas: botón **Producción por faltantes**. Calcula faltantes por variante y prepara un grupo solamente por lo que no alcanza en stock.
- Las OF creadas desde venta conservan el pedido en **Origen** y quedan vinculadas al grupo, cliente, vendedor y encargado.
- Talla/color/modelo se manejan con las **variantes estándar de Odoo**.
- Se conserva valoración automática y el control ESI de Producción en Proceso (WIP).
- **Destajos independientes**: ya no pertenecen a una OF, no bloquean el cierre y no aumentan el costo del producto. Al confirmar se contabilizan como gasto de sueldos/extras contra Destajos por Pagar.
- No se calculan tiempos de destajo.

## Flujo recomendado

1. Venta: cargar las variantes y cantidades.
2. Pulsar **Producción por faltantes**.
3. Revisar el grupo y sus LdM.
4. Si una línea no tiene LdM, usar el botón **LdM** para crearla/editarla.
5. Pulsar **Crear órdenes de producción**.
6. Desde el grupo abrir las OF, los materiales consolidados o las LdM.
7. Los reportes del módulo `esi_produccion_report_v13` incluyen el resumen consolidado del grupo.
