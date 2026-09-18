from odoo import fields, models

class SdStockLocation(models.Model):
    _inherit = "stock.location"

    journal_id = fields.Many2one('account.journal',string='Diario valoracion')