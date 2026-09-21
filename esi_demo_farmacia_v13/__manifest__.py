# -*- coding: utf-8 -*-
{
    'name': 'ESI - Demo Farmacia Odoo 13',
    'version': '13.0.1.2.0',
    'summary': 'Demo integral ESI: sucursales, ventas, compras, POS, inventario y reportes financieros',
    'description': '''
Demo integral para validar el paquete básico ESI en Odoo 13.

Carga datos de prueba para una farmacia: plan contable básico, Balance General,
Estado de Resultados, dos sucursales/almacenes, Tipos de Venta y Compra,
productos con costo promedio y valoración automática, POS y operaciones de
compras/ventas.

USAR EXCLUSIVAMENTE EN BASES DE PRUEBA.
    ''',
    'author': 'ESI - Especialistas en Sistemas Integrados',
    'maintainer': 'ESI - Especialistas en Sistemas Integrados',
    'website': 'https://esibolivia.store',
    'category': 'ESI/Demo',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'purchase_stock',
        'stock_account',
        'point_of_sale',
        'esi_base_multi_store',
        'esi_stock_multi_store',
        'esi_account_multi_store',
        'esi_sale_multi_store',
        'esi_purchase_multi_store',
        'esi_bi_automated_sale_order',
        'esi_bi_automated_purchase_order',
        'esi_automated_sale_multi_store',
        'esi_automated_purchase_multi_store',
        'esi_bi_financial_pdf_reports',
        'esi_bi_financial_excel_reports',
        'esi_ventas_report_v13',
        'esi_compras_report_v13',
        'esi_st_kardex',
        'esi_sd_pos_report_v13',
        'esi_sd_account_v13',
        'esi_sd_comprobantes_contable',
        'esi_sd_links_documentos',
        'esi_sd_stock_v13',
    ],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}
