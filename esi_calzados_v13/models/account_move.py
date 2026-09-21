# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    esi_mrp_production_id = fields.Many2one(
        'mrp.production', string='OF ESI relacionada', copy=False, index=True,
        help='Orden de fabricación relacionada con asientos provisionales de Producción en Proceso.'
    )
    esi_wip_kind = fields.Selection([
        ('material', 'Materiales en proceso'),
        ('reversal', 'Reversión materiales en proceso'),
    ], string='Tipo WIP ESI', copy=False)
