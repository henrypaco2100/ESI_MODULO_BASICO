from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from datetime import datetime
class SdInheritAccountPaymentMejoras(models.Model):
    _inherit = "account.payment"

    sd_is_anticipo = fields.Boolean('Es Anticipo')
    sd_glosa = fields.Char('Glosa')

    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id', 'sd_is_anticipo')
    def _compute_destination_account_id(self):
        vals = super(SdInheritAccountPaymentMejoras, self)._compute_destination_account_id()
        for payment in self:
            if self.sd_is_anticipo:
                if payment.partner_id:
                    partner = payment.partner_id.with_context(force_company=payment.company_id.id)
                    if payment.partner_type == 'customer':
                        payment.destination_account_id = partner.sd_cuenta_anticipo.id
                        print(payment.destination_account_id, '--------------------------------')
        return vals

    def crear_archivo_adjunto_recibo(self):
        pdf = self.env.ref('account.action_report_payment_receipt').render_qweb_pdf(self.ids)
        b64_pdf = base64.b64encode(pdf[0])
        return b64_pdf
    def crear_archivo_adjunto_comprobante(self):
        pdf = self.env.ref('sd_comprobantes_contable.sd_action_account_payment_comprobantes').render_qweb_pdf(self.ids)
        b64_pdf = base64.b64encode(pdf[0])
        return b64_pdf

    def post(self):
        vals = super(SdInheritAccountPaymentMejoras, self).post()
        gestion = self.payment_date.strftime('%Y')
        hora_actual = self.payment_date.strftime('%d/%m/%Y') + ' ' + datetime.now().strftime('%H:%M:%S')
        fecha = datetime.strptime(hora_actual, '%d/%m/%Y %H:%M:%S')
        recibo_pdf, comprobante_pdf = self.crear_archivo_pdf()
        recibo_pdf_id = self.env['pdf.viewer'].create({'sd_archivo': recibo_pdf})
        comprobante_pdf_id = self.env['pdf.viewer'].create({'sd_archivo': comprobante_pdf})
        historial_tran = {
            'sd_fecha_emision': fecha,
            'partner_id': self.partner_id.id,
            'sd_monto': self.amount,
            'sd_descripcion': self.communication,
            'sd_gestion': gestion,
            'pago_id': self.id,
            'sd_pdf_viewer_recibo_id': recibo_pdf_id.id,
            'sd_pdf_viewer_comprobante_id': comprobante_pdf_id.id
        }
        self.env['historial.transaccion'].create(historial_tran)

        for move_line in self.move_line_ids:
            move_line.update({'name': self.communication})
        return vals

    def crear_archivo_pdf(self):
        recibo_pdf = None  # self.crear_archivo_adjunto_recibo()
        comprobante_pdf = None  # self.crear_archivo_adjunto_comprobante()
        return recibo_pdf,comprobante_pdf