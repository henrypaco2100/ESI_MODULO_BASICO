from odoo import models, fields, api, _
from odoo.exceptions import UserError
class SdRastreoPaymentOrigin(models.Model):
    _name = 'rastreo.payment.origin'

    model_id = fields.Char('Modelo')
    payment_id = fields.Many2one('account.payment')
    sd_descripcion = fields.Char('Descripcion')
    sd_monto = fields.Float('Monto')