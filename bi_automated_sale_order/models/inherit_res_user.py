from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from datetime import date,datetime
from odoo.exceptions import UserError, ValidationError
class SdInheritMultiAutomateSale(models.Model):
    _inherit='res.users'
    automated_sale_ids = fields.Many2many(
        'automated.sale',
        'res_automate_sale_users_rel',
        'user_id',
        'cid',
        'Tipo de Ventas',
    )