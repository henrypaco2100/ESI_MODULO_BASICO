# sd_comprobantes_contable - actualización ESI 2026-09-01

## Cambios
- Nuevo bloque **Comprobante Contable** en `account.move` > **Otra información**.
- Se conserva y mueve `sd_is_fecha` (**Columna Fecha**).
- Nuevo `sd_show_cash_flow` (**Mostrar CTA Flujo**).
- Nuevo `sd_show_analytic` (**Mostrar Analítica**).
- Los dos formatos de comprobante de `account.move` muestran las columnas de forma independiente.
- CTA Flujo usa `account.move.line.esi_cash_flow_id` de `bi_financial_pdf_reports`.
- Analítica usa el campo estándar `account.move.line.analytic_account_id` de Odoo 13.
- Dependencias explícitas con `bi_financial_pdf_reports` y `bi_financial_excel_reports`.
- Tabla de líneas refactorizada para evitar mantener combinaciones duplicadas de columnas.

## Nota sobre Columna Fecha
`sd_is_fecha` ya existía. Su finalidad es incluir o no una columna de fecha en las líneas del PDF. Se mantiene el nombre técnico para conservar los valores existentes al actualizar el módulo. En esta versión se imprime `account.move.line.date` (fecha contable de la línea).


## ESI corrección 2026-09-01 - Conversión de importes a letras
- Corregido `NameError: lista_centana is not defined` en `report/report_account_move.py`.
- El arreglo se define y se consulta de forma consistente como `lista_centena`.
- Esta falla era un typo histórico del módulo original y se manifestaba al imprimir el total del comprobante en letras.
