 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

#DAVID MODELO HEREDADO PARA PODER AGREGAR BOTONES EN LAS TRANSFERECNIAS


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sd_tipo = fields.Selection([
        ('venta', 'Venta'),
        ('compra', 'Compra'),
        ('produccion', 'Produccion'),
        ('other', 'Other')
    ], string="tipo", readonly=True, compute="_tipo_entry", store=False, invisible="1")

    @api.depends('name')
    def _tipo_entry(self):
        sd_tipo = 'other'
        tipo = self.picking_type_id.code
        if tipo == 'incoming': sd_tipo = 'compra'
        if tipo == 'outgoing': sd_tipo = 'venta'
        if tipo == 'mrp_operation': sd_tipo = 'produccion'
        # print('sd_tipo: ', sd_tipo)
        self.update({
            'sd_tipo': sd_tipo
        })

    #MOVIMIENTOS DE PRODUCTOS
    def action_get_stock_picking(self):
        self.ensure_one()
        array = []
        for move in self.move_line_ids:
            array.append(move.id)
        move_id = self.env['stock.move.line'].search([('id', 'in', array)])
        # if len(move_id) > 1:
        return {
            'name': _('Movimiento productos'),
            'view_mode': 'tree,form',
            'res_model': 'stock.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_id.ids)],
        }
        # elif len(move_id) == 1:
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'stock.move.line',
        #         'view_mode': 'form',
        #         'views': [[self.env.ref('stock.view_move_line_form').id, 'form']],
        #         'res_id': move_id.id,
        #         'target': 'current',
        #     }

    #VENTAS
    def action_get_sale_moves(self):
        self.ensure_one()
        if 'sale.order' in self.env:
            sale = self.env['sale.order'].search([('id', '=', self.sale_id.id)])
            if len(sale) != 1:
                return {
                    'name': _('Ventas'),
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', sale.ids)],
                }
            elif len(sale) == 1:
                return {
                    'name': _('Venta'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'view_mode': 'form',
                    'views': [[self.env.ref('sale.view_order_form').id, 'form']],
                    'res_id': sale.id,
                    'target': 'current',
                }

    #COMPRAS
    def action_get_purchase_moves(self):
        self.ensure_one()
        if 'purchase.order' in self.env:
            purchase = self.env['purchase.order'].search([('id', '=', self.purchase_id.id)])
            if len(purchase) != 1:
                return {
                    'name': _('Compras'),
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', purchase.ids)],
                }
            elif len(purchase) == 1:
                return {
                    'name': _('Compra'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'form',
                    'views': [[self.env.ref('purchase.purchase_order_form').id, 'form']],
                    'res_id': purchase.id,
                    'target': 'current',
                }
