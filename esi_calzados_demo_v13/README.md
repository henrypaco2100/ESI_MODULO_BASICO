# ESI Calzados Demo v13

Demo de 3 productos terminados con variantes, listas de materiales, destajos, cuentas analíticas y valoración automática.

## Corrección 13.0.3.0.1
El `post_init_hook` se exporta correctamente desde `__init__.py` para que Odoo 13 pueda ejecutarlo durante la instalación.

## Productos demo
- Bota Lona ESI Demo
- Bota Puro Cuero ESI Demo
- Tenis Táctico ESI Demo

La demo crea cuentas/parametrización si no existen, categorías AVCO con valoración automática, ubicación de Producción con cuenta WIP, materias primas, proveedor, variantes Talla/Color, LdM, cuentas analíticas, 3 OF y destajos en borrador.
