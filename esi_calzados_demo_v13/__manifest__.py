# -*- coding: utf-8 -*-
{
    'name': 'ESI Calzados - Demo v13',
    'version': '13.0.3.2.2',
    'category': 'Manufacturing',
    'summary': 'Demo ESI: 3 calzados, variantes, LdM, destajos, analítica y valoración automática',
    'description': '''
Demo para ESI Calzados v13.

Desde Fabricación > Configuración > ESI Demo Calzados, el botón CREAR / ACTUALIZAR DEMO crea o actualiza:
- 3 productos terminados con variantes de Talla y Color.
- 3 listas de materiales.
- Materias primas con costos y proveedor demo.
- Categorías AVCO con valoración automática.
- Cuenta 154000 Producción en Proceso y configuración contable relacionada.
- Cuentas analíticas de producción.
- Actividades de destajo, 3 OF demo y 9 destajos en borrador.

La carga se realiza desde el asistente para que cualquier incompatibilidad de la base se muestre de forma controlada sin romper la instalación del módulo.
    ''',
    'author': 'ESI - Especialistas en Sistemas Integrados',
    'license': 'LGPL-3',
    'depends': ['esi_calzados_v13', 'esi_produccion_report_v13'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/demo_loader_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
