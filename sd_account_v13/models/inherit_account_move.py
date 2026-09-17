from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SdInheritAccountMoveMejoras(models.Model):
    _inherit = "account.move"
    sd_glosa = fields.Char('Glosa')
    # sd_show_glosa = fields.Boolean()
    # sd_tipo_movimiento = fields.Selection([('egreso', 'Egreso'),
    #                                        ('ingreso', 'Ingreso'),
    #                                        ('traspaso', 'Traspaso'),],
    #                                       string='Tipo Transferencia')

    # @api.onchange('sd_show_glosa')
    # def get_pago(self):
    #     array_pagos = []
    #     if self.type == 'in_invoice':
    #         pagos_con_factura = self.env['account.payment'].search([('payment_type', '=', 'outbound'),
    #                                                                 ('move_reconciled', '=', True)])
    #         for pago in pagos_con_factura:
    #             for factura in pago.reconciled_invoice_ids:
    #                 if factura == self:
    #                     array_pagos.append(pago.id)
    #     elif self.type == 'out_invoice':
    #         pagos_con_factura = self.env['account.payment'].search([('payment_type', '=', 'inbound'),
    #                                                                 ('move_reconciled', '=', True)])
    #         for pago in pagos_con_factura:
    #             for factura in pago.reconciled_invoice_ids:
    #                 if factura == self:
    #                     array_pagos.append(pago.id)
    #     else:
    #         for pago in self.line_ids:
    #             if pago.payment_id.id not in array_pagos:
    #                 array_pagos.append(pago.payment_id.id)
    #
    #     account_payment = self.env['account.payment'].search([('id', 'in', array_pagos)])
    #     self.sd_glosa = account_payment.communication

    @api.depends('journal_id')
    def _verificar_usuario_permisos(self):
        print('-----------------------------------------------------------------------------------------')
        for account_move in self:
            print('funcion computarizada ------------------------------------------------------------')
            permiso_contabilidad_contable = self.env['res.users'].has_group('account.group_account_user')
            if permiso_contabilidad_contable:
                account_move.update({
                    'sd_tiene_contabilidad_completa': False
                })
            else:
                account_move.update({
                    'sd_tiene_contabilidad_completa': True
                })

    sd_tiene_contabilidad_completa = fields.Boolean('Sin Contabilidad Completa',  copy=False)
    def button_cancel(self):
        if not self.env['res.users'].has_group('sd_account_v13.sd_grupo_cancelar_account_move_mejoras'):
            raise UserError(_("No tiene permiso para Cancelar Asientos."))
        res = super(SdInheritAccountMoveMejoras, self).button_cancel()
        return res

    def button_draft(self):
        if not self.env['res.users'].has_group('sd_account_v13.sd_grupo_cancelar_account_move_mejoras'):
            raise UserError(_("No tiene permiso para Cambiar a Borrador facturas o asientos."))
        res = super(SdInheritAccountMoveMejoras, self).button_draft()
        return res