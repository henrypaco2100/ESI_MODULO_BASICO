from odoo import fields, models, api, _

class SdCargarSaldoContableWizard(models.TransientModel):
    _name = "cargar.saldo.contable"
    def action_cargar_saldo_contable(self):
        account_move_ids = self.env['account.move.line'].search([])
        for move_id in account_move_ids:
            move_id._compute_saldo()