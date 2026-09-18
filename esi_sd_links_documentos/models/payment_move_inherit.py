 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

#DAVID MODELO HEREDADO PARA PODER AGREGAR BOTONES EN LOS PAGOS DE CONTABLIDAD


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    sd_tipo = fields.Selection([
        ('venta', 'Venta'),
        ('compra', 'Compra'),
        ('transferencia', 'Transferencia')
    ], string="venta", readonly=True, compute="_payment_type", store=False, invisible="1")

    @api.depends('reconciled_invoice_ids')
    def _payment_type(self):
        sd_tipo = 'transferencia'
        if self.move_reconciled:
            for factura in self.reconciled_invoice_ids:
                if factura.sd_tipo == 'in_invoice': sd_tipo = 'compra'
                if factura.sd_tipo == 'out_invoice': sd_tipo = 'venta'
        self.update({
            'sd_tipo': sd_tipo
        })


    def action_get_account_moves(self):
        self.ensure_one()
        if 'account.move' in self.env:
            moves_names = self.move_name.split('§§')

            account_move = self.env['account.move'].search([('name', 'in', moves_names)])

            if len(account_move) != 1:
                return {
                    'name': _('Asiento Contable'),
                    'view_mode': 'tree,form',
                    'res_model': 'account.move',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', account_move.ids)],
                }
            elif len(account_move) == 1:
                return {
                    'name': _('Asiento Contable'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'views': [[self.env.ref('account.view_move_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }

    # ESTE METODO ESTA SOBREESCRIBIENDO AL DEL MODULO account, MODELO account_payment (link a facturas)
    def button_invoices(self):
        self.ensure_one()
        if 'account.move' in self.env:
            array_facturas = []
            for factura in self.reconciled_invoice_ids:
                array_facturas.append(factura.id)
            account_move = self.env['account.move'].search([('id', 'in', array_facturas)])

            if len(account_move) > 1:
                return {
                    'name': _('Facturas'),
                    'view_mode': 'tree,form',
                    'res_model': 'account.move',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', account_move.ids)],
                }
            elif len(account_move) == 1:
                return {
                    'name': _('Factura'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'views': [[self.env.ref('account.view_move_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }

    def action_get_compra(self):
        self.ensure_one()
        if 'account.payment' in self.env:
            array_compras = []
            for factura in self.reconciled_invoice_ids:
                if factura.invoice_origin not in array_compras:
                    array_compras.append(factura.invoice_origin)
            account_move = self.env['purchase.order'].search([('name', 'in', array_compras)])
            if len(account_move) > 1:
                return {
                    'name': _('Compras'),
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', account_move.ids)],
                }
            elif len(account_move) == 1:
                return {
                    'name': _('Compra'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'form',
                    'views': [[self.env.ref('purchase.purchase_order_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }

    def action_get_venta(self):
        self.ensure_one()
        if 'account.payment' in self.env:
            array_ventas = []
            for factura in self.reconciled_invoice_ids:
                if factura.invoice_origin not in array_ventas:
                    array_ventas.append(factura.invoice_origin)
            account_move = self.env['sale.order'].search([('name', 'in', array_ventas)])

            if len(account_move) > 1:
                return {
                    'name': _('Ventas'),
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', account_move.ids)],
                }
            elif len(account_move) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'view_mode': 'form',
                    'views': [[self.env.ref('sale.view_order_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }
