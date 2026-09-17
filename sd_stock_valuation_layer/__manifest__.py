# -*- coding: utf-8 -*-
{'name': 'Valoracion del Inventario y Reprocesar',
 'version': '13.0.0.3',
 'category': 'Inventario',
 'description': '\n'
                '    Este modulo tiene la funcion que permiten las mejoras de la valoracion de inventario y el '
                'Reprocesar',
 'summary': 'Módulo histórico de valoración temporalmente deshabilitado por ESI',
 'sequence': '10',
 'author': 'ESI - Especialistas en Sistemas Integrados',
 'maintainer': 'ESI - Especialistas en Sistemas Integrados',
 'depends': ['stock_account'],
 'data': ['security/create_grupo.xml',
          'security/ir.model.access.csv',
          'wizard/wizard_reprocesar.xml',
          'view/inherit_res_config_settings.xml',
          'view/management_company.xml',
          'view/inherit_res_company.xml',
          'view/inherit_stock_location.xml'],
 'demo': [],
 'installable': False,
 'application': False,
 'auto_install': False,
 'website': 'https://esibolivia.store'}
