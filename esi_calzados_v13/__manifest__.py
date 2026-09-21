# -*- coding: utf-8 -*-
{
    'name': 'ESI Calzados - Complemento MRP',
    'version': '13.0.3.0.3',
    'category': 'Manufacturing',
    'summary': 'Costos, faltantes, destajos, analítica y valoración automática para calzado',
    'description': """
Complemento para Fabricación estándar de Odoo 13.
No reemplaza MRP ni depende de módulos de procesos personalizados.
Agrega ficha de costos en componentes, faltantes, preparación de RFQ,
registro de destajos sin tiempos, cuenta analítica por OF y soporte para
valoración automática Materia Prima -> Producción en Proceso -> Producto Terminado.
    """,
    'author': 'ESI - Especialistas en Sistemas Integrados',
    'license': 'LGPL-3',
    'depends': [
        'mrp', 'mrp_account', 'purchase_stock', 'stock_account', 'account', 'analytic', 'mail'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/product_template_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/destajo_views.xml',
        'wizard/material_purchase_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
