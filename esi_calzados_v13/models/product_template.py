# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    esi_production_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta analítica de producción',
        help='Cuenta analítica sugerida para las órdenes de fabricación de este producto.'
    )
