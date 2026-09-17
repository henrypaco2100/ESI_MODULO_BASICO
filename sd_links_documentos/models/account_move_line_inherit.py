 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'account.move.line'
    sd_tipo = fields.Selection(related='move_id.sd_tipo')
    # ASIENTOS CONTABLES
    def action_get_account_moves(self):
        self.ensure_one()
        if 'stock.move' in self.env:
            account_move = self.env['account.move'].search([('id', '=', self.move_id.id)])
            if len(account_move) != 1:
                return {
                    'name': _('Asientos Contables'),
                    'view_mode': 'tree,form',
                    'res_model': 'account.move',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', account_move.ids)],
                }
            elif len(account_move) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'views': [[self.env.ref('account.view_move_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }

