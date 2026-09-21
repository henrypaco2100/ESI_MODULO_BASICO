# -*- coding: utf-8 -*-
{
    'name': 'ESI Calzados - Demo v13',
    'version': '13.0.3.1.0',
    'category': 'Manufacturing',
    'summary': 'Demo segura: 3 calzados, variantes, LdM, destajos, analítica y valoración automática',
    'description': '''
Demo para ESI Calzados v13.

IMPORTANTE: esta versión NO ejecuta una carga pesada durante la instalación.
Primero se instala el módulo y luego se carga/actualiza la demo desde:
Fabricación > Configuración > ESI Demo Calzados.

De esta manera, si existe alguna particularidad del plan contable o de módulos
personalizados de la base, Odoo muestra un error controlado sin abortar la
instalación ni perder la conexión.
    ''',
    'author': 'ESI - Especialistas en Sistemas Integrados',
    'license': 'LGPL-3',
    'depends': ['esi_calzados_v13'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/demo_loader_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
