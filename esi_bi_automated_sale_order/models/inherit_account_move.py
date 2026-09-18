from odoo import models, fields, api, _

class InheritAccountMoveAutoSale(models.Model):
    _inherit = 'account.move'
    _descripcion = 'Henrencia para el Automated Sale'
    sd_numero_recibo = fields.Char(string='Nro Recibo')
    sd_numero_factura = fields.Char(string='Nro Factura')
    sd_is_numero_factura = fields.Boolean(default=False)
    sd_is_numero_recibo = fields.Boolean(default=False)

    sd_ref_entrega_sale = fields.Char(string='Nota de entrega')
    sd_is_ref_sale = fields.Boolean(default=False)
