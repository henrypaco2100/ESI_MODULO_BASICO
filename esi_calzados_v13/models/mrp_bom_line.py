# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    esi_material_group = fields.Selection(
        [
            ('structure', 'Estructura'),
            ('utensils', 'Utensilios'),
            ('packaging', 'Empaque'),
            ('other', 'Otros'),
        ],
        string='Detalle / Grupo',
        default='structure',
        help='Clasificación visual del material para la ficha de costo de producción.',
    )
