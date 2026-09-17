from odoo import models, fields, api, _
from odoo.exceptions import UserError
class SdHistorialTransaccion(models.Model):
    _name = 'historial.transaccion'

    sd_fecha_emision = fields.Datetime(string='Fecha emisión')
    sd_gestion = fields.Char('Gestión')
    sd_razon_social = fields.Char('Razón social', related='partner_id.name')
    sd_descripcion = fields.Char('Descripción')
    sd_monto = fields.Float('Monto')
    partner_id = fields.Many2one('res.partner', 'cliente')
    pago_id = fields.Many2one('account.payment', 'pago')
    sd_pdf_viewer_recibo_id = fields.Many2one('pdf.viewer', string='Recibo')
    sd_pdf_viewer_comprobante_id = fields.Many2one('pdf.viewer', string='Recibo')
    def action_view_account_payment(self):
        if self.pago_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'views': [[self.env.ref('account.view_account_payment_form').id, 'form']],
                'res_id': self.pago_id.id,
                'target': 'current',
            }

    def action_view_recibo_pago(self):
        if self.sd_pdf_viewer_recibo_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pdf.viewer',
                'view_mode': 'form',
                'views': [[self.env.ref('sd_account_v13.sd_form_pdf_viewer').id, 'form']],
                'res_id': self.sd_pdf_viewer_recibo_id.id,
                'target': 'new',
            }

    def action_view_comprobante_pago(self):
        if self.sd_pdf_viewer_comprobante_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pdf.viewer',
                'view_mode': 'form',
                'views': [[self.env.ref('sd_account_v13.sd_form_pdf_viewer').id, 'form']],
                'res_id': self.sd_pdf_viewer_comprobante_id.id,
                'target': 'new',
            }
