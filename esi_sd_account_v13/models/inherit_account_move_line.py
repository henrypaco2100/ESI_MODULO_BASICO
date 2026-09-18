from odoo import models, fields, api, _
from odoo.exceptions import UserError
import inspect
# from odoo.odoo.tools import get_lang



class SdInheritAccountMoveLineMejorasLuis(models.Model):
    _inherit = 'account.move.line'
    sd_saldo = fields.Monetary("Saldo", default=0.0)
    _order = "date asc"

    # @api.depends('debit', 'credit')
    # def _compute_saldo(self):
    #     for line in self:
    #         line.sd_saldo = line.debit - line.credit
    def action_view_account_move(self):
        if self.move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'views': [[self.env.ref('account.view_move_form').id, 'form']],
                'res_id': self.move_id.id,
                'target': 'current',
            }

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(SdInheritAccountMoveLineMejorasLuis, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                 lazy=lazy)
        if 'sd_saldo' in fields:
            for line in res:
                if '__domain' in line:
                    # line['sd_saldo'] = 0.0
                    # lines = self.search(line['__domain'])
                    # saldo_recorrido = 0
                    # for record in lines:
                    #     record.sd_saldo = 0
                    #     record.sd_saldo = saldo_recorrido + (record.debit - record.credit)
                    #     saldo_recorrido = saldo_recorrido + (record.debit - record.credit)
                    line['sd_saldo'] = line['debit'] - line['credit']

        return res

    # REMOVER CONCILIACIONES SOLO CUANDO SE CANCELE
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        # Payment partial reconcile
        rec_partial_reconcile = self.mapped('matched_debit_ids') + self.mapped('matched_credit_ids')
        if self.env.context.get('move_id'):
            # If an invoice is specified, we will only remove the reconciliation between the payment
            # and that specific invoice.
            # Note that, if a write-off was created this one must be removed too.
            current_invoice = self.env['account.move'].browse(self.env.context.get('move_id'))
            # Current invoice partial reconcile
            invoice_wo_partial_reconcile = current_invoice.line_ids.mapped(
                'matched_debit_ids') + current_invoice.line_ids.mapped('matched_credit_ids')
            writeoff = current_invoice.line_ids.mapped('full_reconcile_id.exchange_move_id')
            if writeoff:
                # Write-off partial reconcile
                invoice_wo_partial_reconcile += writeoff.line_ids.mapped('matched_credit_ids')
                invoice_wo_partial_reconcile += writeoff.line_ids.mapped('matched_debit_ids')
            rec_partial_reconcile = rec_partial_reconcile & invoice_wo_partial_reconcile
        if inspect.stack()[1].function != 'button_draft':
            rec_partial_reconcile.unlink()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # sd_filter_uom = self.env['ir.config_parameter'].sudo().get_param('stock.sd_filter_uom')
        # if sd_filter_uom:
        #     return super(SdInheritAccountMoveLineMejorasLuis, self)._onchange_product_id()

        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
            line.tax_ids = taxes
            sd_filter_uom = self.env['ir.config_parameter'].sudo().get_param('stock.sd_filter_uom')
            line.price_unit = line._get_computed_price_unit()
            if sd_filter_uom:
                line.product_uom_id = line._get_computed_uom()
                return {'domain': {'product_uom_id': [('category_id', '=', self.product_uom_id.category_id.id)]}}
        # if len(self) == 1:

        return
