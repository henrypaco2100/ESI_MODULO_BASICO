# ESI Calzados - Demo v13 13.0.3.1.0

## Corrección principal
Esta versión elimina el `post_init_hook` pesado que podía abortar la instalación y dejar el navegador en **Intentando reconectar**.

El módulo se instala primero de forma limpia. Luego:

**Fabricación > Configuración > ESI Demo Calzados > CREAR / ACTUALIZAR DEMO**

La carga es idempotente y puede ejecutarse nuevamente.

## Crea
- 3 productos terminados con Talla / Color.
- 3 LdM.
- 22 materias primas con costo.
- Actividades de destajo y 9 destajos en borrador.
- 3 OF demo (opcional desde el checkbox).
- Cuentas analíticas de producción.
- Categorías AVCO + valoración automática.
- Cuenta 153000 Materias primas.
- Cuenta 154000 Producción en Proceso.
- Cuenta 155000 Producto Terminado.
- Cuenta 215500 Destajos por pagar.
- Diario ESIPR.

## Compatibilidad
Depende únicamente de `esi_calzados_v13`; no depende de módulos de procesos.
Está diseñado para convivir con ESI_MODULO_BASICO y reutiliza cuentas por código si ya existen.
