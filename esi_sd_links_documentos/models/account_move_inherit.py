 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

#DAVID MODELO HEREDADO PARA PODER AGREGAR BOTONES EN LAS FACTURAS DE CONTABLIDAD


class AccountMove(models.Model):
    _inherit = 'account.move'
    sd_tipo = fields.Selection([
        ('venta', 'Venta Inventario'),
        ('compra', 'Compra Inventario'),
        ('pos', 'Punto de Venta Inventario'),
        ('production', 'Produccion Inventario'),
        ('pago_proveedor', 'Pago a Proveedor'),
        ('pago_cliente', 'Pago de Cliente'),
        ('pago_transferencia', 'Pago Transferencia'),
        ('pago_multiple', 'Pago Multiple'),
        ('in_invoice', 'Factura proveedor'),
        ('out_invoice', 'Factura Cliente'),
        ('other', 'Otros')
    ] ,string="venta", readonly=True, compute="_tipo_entry", store=False, invisible="1")

    @api.depends('stock_move_id')
    def _tipo_entry(self):
        for line in self:
            sd_tipo = 'other'
            if line.type == 'entry':
                if line.stock_move_id.sale_line_id:
                    sd_tipo = 'venta'
                if line.stock_move_id.purchase_line_id:
                    sd_tipo = 'compra'
                if line.stock_move_id.picking_id and not line.stock_move_id.purchase_line_id and not line.stock_move_id.sale_line_id:
                    sd_tipo = 'pos'
                # if hasattr(line, 'production_id'):
                if line.stock_move_id.location_dest_id.usage == 'production' or line.stock_move_id.location_id.usage == 'production':
                    sd_tipo = 'production'
                if 'pos.order' in line.env:
                    line.env['pos.order'].search([('name', '=', line.stock_move_id.picking_id.origin)])
                    tipo = 'production'
                if not line.stock_move_id and line.ref:
                    tipo_pago = line.get_tipo_pagos()
                    if tipo_pago == 'cobro':
                        sd_tipo = 'pago_cliente'
                    if tipo_pago == 'pago':
                        sd_tipo = 'pago_proveedor'
                    if tipo_pago == 'transferencia':
                        sd_tipo = 'pago_transferencia'
                    if tipo_pago == 'multiple':
                        sd_tipo = 'pago_multiple'
            elif line.type == 'in_invoice':
                sd_tipo = 'in_invoice'
            elif line.type == 'out_invoice':
                sd_tipo = 'out_invoice'
            line.update({
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

    # PAGOS CLIENTE, PROVEEDOR, TRANSFERENCIA Y MULTIPLE
    def action_get_payment(self):
        self.ensure_one()
        array_pagos = []
        if self.type == 'in_invoice':
            pagos_con_factura = self.env['account.payment'].search([('payment_type', '=', 'outbound'),
                                                                    ('move_reconciled', '=', True)])
            for pago in pagos_con_factura:
                for factura in pago.reconciled_invoice_ids:
                    if factura == self:
                        array_pagos.append(pago.id)
        elif self.type == 'out_invoice':
            pagos_con_factura = self.env['account.payment'].search([('payment_type', '=', 'inbound'),
                                                                    ('move_reconciled', '=', True)])
            for pago in pagos_con_factura:
                for factura in pago.reconciled_invoice_ids:
                    if factura == self:
                        array_pagos.append(pago.id)
        else:
            for pago in self.line_ids:
                if pago.payment_id.id not in array_pagos:
                    array_pagos.append(pago.payment_id.id)

        account_payment = self.env['account.payment'].search([('id', 'in', array_pagos)])

        name_title = ''
        if self.sd_tipo == 'out_invoice': name_title = 'Pagos Cliente'
        if self.sd_tipo == 'in_invoice': name_title = 'Pagos Proveedor'
        if self.sd_tipo == 'pago_transferencia': name_title = 'Pagos Transferencia'
        if self.sd_tipo == 'pago_multiple': name_title = 'Pagos Multiple'

        if len(account_payment) != 1:
            return {
                'name': _(name_title),
                'view_mode': 'tree,form',
                'res_model': 'account.payment',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', account_payment.ids)],
            }
        elif len(account_payment) == 1:
            return {
                'name': _(name_title),
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'views': [[self.env.ref('account.view_account_payment_form').id, 'form']],
                'res_id': account_payment.id,
                'target': 'current',
            }

    #VENTAS
    def action_get_sale_moves(self):
        self.ensure_one()
        if self.type == 'entry':
            sale_id = self.env['sale.order'].search(
                [('name', '=', self.stock_move_id.sale_line_id.order_id.name),
                 ('state', '=', 'sale')])
            if not sale_id:
                sale_id = self.buscar_venta_por_factura()
        else:
            sale_id = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
        if len(sale_id) != 1:
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
        if self.type == 'entry':
            purchase_id = self.env['purchase.order'].search(
                [('name', '=', self.stock_move_id.purchase_line_id.order_id.name),
                 ('state', '=', 'purchase')])
            if not purchase_id:
                purchase_id = self.buscar_compra_por_factura()
        else:
            purchase_id = self.env['purchase.order'].search(
                [('invoice_ids.name', '=', self.name), ('state', '=', 'purchase')])
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
            production_id = self.env['mrp.production'].search([('name', '=', self.stock_move_id.reference)])

            if len(production_id) != 1:
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
            if self.stock_move_id.picking_id.origin:
                order_pos = self.stock_move_id.picking_id.origin.replace(' ', '').split('-')
                point_of_sale_id = self.env['pos.order'].search([('name', '=', order_pos[1] if len(order_pos) > 2 else order_pos)])
                if len(point_of_sale_id) != 1:
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

    # FACTURA PROVEEDOR
    def action_get_payment_moves_supplier(self):
        self.ensure_one()
        account_id = self.buscar_factura_por_pago()
        if len(account_id) != 1:
            return {
                'name': _('Factura Proveedor'),
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', account_id.ids)],
            }
        elif len(account_id) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'views': [[self.env.ref('account.view_move_form').id, 'form']],
                'res_id': account_id.id,
                'target': 'current',
            }

    # FACTURA CLIENTE
    def action_get_payment_moves_client(self):
        self.ensure_one()
        account_id = self.buscar_factura_por_pago()
        if len(account_id) != 1:
            return {
                'name': _('Factura Cliente'),
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', account_id.ids)],
            }
        elif len(account_id) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'views': [[self.env.ref('account.view_move_form').id, 'form']],
                'res_id': account_id.id,
                'target': 'current',
            }
    def buscar_factura_por_pago(self):
        """Buscar Factura proveedor o cliente
        return:  move_ids"""
        array_pagos = []
        for pago in self.line_ids:
            if pago.payment_id.id not in array_pagos:
                array_pagos.append(pago.payment_id.id)
                break
        account_payment_id = self.env['account.payment'].search([('id', 'in', array_pagos)])
        move_ids = account_payment_id.reconciled_invoice_ids
        return move_ids
    def buscar_compra_por_factura(self):
        move_ids = self.buscar_factura_por_pago()
        purchase_ids = self.env['purchase.order'].search([('name','in',[move_id.invoice_origin for move_id in move_ids])])
        return purchase_ids
    def buscar_venta_por_factura(self):
        move_ids = self.buscar_factura_por_pago()
        sale_ids = self.env['sale.order'].search([('name','in',[move_id.invoice_origin for move_id in move_ids])])
        return sale_ids