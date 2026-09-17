 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = 'stock.move.line'
    sd_tipo = fields.Selection([
        ('venta', 'Venta'),
        ('compra', 'Compra'),
        ('pos', 'Punto de Venta'),
        ('transferencia', 'Transferencia'),
        ('production', 'Production'),
        ('other', 'Otros')
    ] ,string="venta", readonly=True, compute="_tipo_entry", invisible="1")

    @api.depends('move_id')
    def _tipo_entry(self):
        sd_tipo = 'other'
        # if self.type == 'entry':
        if self.move_id.sale_line_id:
            sd_tipo = 'venta'
        if self.move_id.purchase_line_id:
            sd_tipo = 'compra'
        if self.move_id.picking_id and not self.move_id.purchase_line_id and not self.move_id.sale_line_id:
            sd_tipo = 'pos'
        # if hasattr(self, 'production_id'):
        if self.move_id.location_dest_id.usage == 'production' or self.move_id.location_id.usage == 'production':
            sd_tipo = 'production'
        if self.location_id.usage == 'internal' and self.location_dest_id.usage == 'internal':
            sd_tipo = 'transferencia'

        self.update({
            'sd_tipo': sd_tipo
        })

    # Funcion para obtener todos los pagos de un asiento contable
    def get_tipo_pagos(self):
        # account_move = self.env['account.move.line'].search([('move_id.name', '=', self.name)])
        pago = False
        cobro = False
        transferencia = False
        tipo_pago = ''
        for asiento in self.line_ids:
            tipo_asiento = asiento.payment_id.payment_type
            if tipo_asiento == 'inbound':
                cobro = True
                tipo_pago = 'cobro'
                if pago or transferencia:
                    tipo_pago = 'multiple'
                    break
            if tipo_asiento == 'outbound':
                pago = True
                tipo_pago = 'pago'
                if cobro or transferencia:
                    tipo_pago = 'multiple'
                    break
            if tipo_asiento == 'transfer':
                transferencia = True
                tipo_pago = 'transferencia'
                if pago or cobro:
                    tipo_pago = 'multiple'
                    break
        return tipo_pago

    # ASIENTOS CONTABLES
    def action_get_transfer_moves(self):
        self.ensure_one()
        if 'stock.move' in self.env:
            stock_picking = self.env['stock.picking'].search([('name', '=', self.reference)])
            if len(stock_picking) != 1:
                return {
                    'name': _('Transferencias'),
                    'view_mode': 'tree,form',
                    'res_model': 'stock.picking',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', stock_picking.ids)],
                }
            elif len(stock_picking) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'view_mode': 'form',
                    'views': [[self.env.ref('stock.view_picking_form').id, 'form']],
                    'res_id': stock_picking.id,
                    'target': 'current',
                }

    # ASIENTOS CONTABLES
    def action_get_account_moves(self):
        self.ensure_one()
        if 'stock.move' in self.env:
            account_move = self.env['account.move'].search([('stock_move_id.id', '=', self.move_id.id)])
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
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'views': [[self.env.ref('account.view_move_form').id, 'form']],
                    'res_id': account_move.id,
                    'target': 'current',
                }


    #VENTAS
    def action_get_sale_moves(self):
        self.ensure_one()
        sale_id = self.env['sale.order'].search([('name', '=', self.origin)])
        if len(sale_id) > 1:
            return {
                'name': _('Venta'),
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', sale_id.ids)],
            }
        elif len(sale_id) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'views': [[self.env.ref('sale.view_order_form').id, 'form']],
                'res_id': sale_id.id,
                'target': 'current',
            }

    #COMPRAS
    def action_get_purchase_moves(self):
        self.ensure_one()
        purchase_id = self.env['purchase.order'].search([('name', '=', self.origin)])
        if len(purchase_id) != 1:
            return {
                'name': _('Compra'),
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', purchase_id.ids)],
            }
        elif len(purchase_id) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'views': [[self.env.ref('purchase.purchase_order_form').id, 'form']],
                'res_id': purchase_id.id,
                'target': 'current',
            }

    # PRODUCCION
    def action_get_production_moves(self):
        self.ensure_one()
        if 'mrp.production' in self.env:
            production_id = self.env['mrp.production'].search([('id', '=', self.production_id.id)])

            if len(production_id) > 1:
                return {
                    'name': _('Production'),
                    'view_mode': 'tree,form',
                    'res_model': 'mrp.production',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', production_id.ids)],
                }
            elif len(production_id) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.production',
                    'view_mode': 'form',
                    'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                    'res_id': production_id.id,
                    'target': 'current',
                }


    # PUNTO DE VENTA
    def action_get_point_of_sale_moves(self):
        self.ensure_one()
        if 'pos.config' in self.env:
            account_move = self.env['account.move'].search([('stock_move_id.id', '=', self.move_id.id)])
            if account_move.stock_move_id.picking_id.origin:
                order_pos = account_move.stock_move_id.picking_id.origin.replace(' ', '').split('-')
                point_of_sale_id = account_move.env['pos.order'].search([('name', '=', order_pos[1] if len(order_pos) > 2 else order_pos)])
                if len(point_of_sale_id) > 1:
                    return {
                        'name': _('Punto de Venta'),
                        'view_mode': 'tree,form',
                        'res_model': 'pos.order',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', point_of_sale_id.ids)],
                    }
                elif len(point_of_sale_id) == 1:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'pos.order',
                        'view_mode': 'form',
                        'views': [[self.env.ref('point_of_sale.view_pos_pos_form').id, 'form']],
                        'res_id': point_of_sale_id.id,
                        'target': 'current',
                    }

