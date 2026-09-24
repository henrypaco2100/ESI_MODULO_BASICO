# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    esi_production_manager_id = fields.Many2one(
        'res.users', string='Encargado de producción',
        default=lambda self: self.env.user if self.env.user.has_group('mrp.group_mrp_user') else False,
        domain="[('share', '=', False)]",
        help='Responsable que recibirá las órdenes de producción creadas para faltantes de esta venta.'
    )
    esi_production_group_ids = fields.One2many(
        'esi.production.group', 'sale_order_id', string='Grupos de producción'
    )
    esi_production_group_count = fields.Integer(
        string='Grupos producción', compute='_compute_esi_production_group_count'
    )

    @api.depends('esi_production_group_ids')
    def _compute_esi_production_group_count(self):
        for order in self:
            order.esi_production_group_count = len(order.esi_production_group_ids)

    def action_view_esi_production_groups(self):
        self.ensure_one()
        action = self.env.ref('esi_calzados_v13.action_esi_production_group').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {
            'default_sale_order_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_salesperson_id': self.user_id.id,
            'default_production_manager_id': self.esi_production_manager_id.id,
            'default_origin': self.name,
        }
        return action

    def _esi_available_qty_for_sale_product(self, product):
        self.ensure_one()
        location = self.warehouse_id.lot_stock_id if self.warehouse_id else False
        product_ctx = product.with_context(location=location.id) if location else product
        if 'free_qty' in product._fields:
            available = product_ctx.free_qty
        else:
            available = product_ctx.qty_available

        # Si el pedido ya fue confirmado, parte del stock puede estar reservado
        # específicamente para esta misma venta. Lo sumamos de vuelta para no
        # interpretar esa reserva propia como un faltante adicional.
        reserved_for_this_sale = 0.0
        for line in self.order_line.filtered(lambda l: l.product_id == product):
            if 'move_ids' not in line._fields:
                continue
            for move in line.move_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id == product):
                qty = move.reserved_availability or 0.0
                if move.product_uom and move.product_uom != product.uom_id and move.product_uom.category_id == product.uom_id.category_id:
                    qty = move.product_uom._compute_quantity(qty, product.uom_id)
                reserved_for_this_sale += qty

        return max(0.0, available + reserved_for_this_sale)

    def _esi_shortage_by_product(self):
        self.ensure_one()
        quantities = OrderedDict()
        for line in self.order_line.filtered(lambda l: l.product_id and l.product_id.type == 'product'):
            product = line.product_id
            qty = line.product_uom._compute_quantity(line.product_uom_qty, product.uom_id)
            quantities[product.id] = quantities.get(product.id, 0.0) + qty

        shortages = []
        for product_id, required in quantities.items():
            product = self.env['product.product'].browse(product_id)
            available = self._esi_available_qty_for_sale_product(product)
            missing = max(0.0, required - available)
            if not float_is_zero(missing, precision_rounding=product.uom_id.rounding or 0.00001):
                shortages.append((product, missing))
        return shortages

    def _esi_fill_production_group_shortages(self, group):
        self.ensure_one()
        shortages = self._esi_shortage_by_product()
        if not shortages:
            raise UserError(_('Todos los productos almacenables de esta venta tienen stock suficiente.'))
        vals_list = []
        Line = self.env['esi.production.group.line']
        for product, missing_qty in shortages:
            vals = {
                'group_id': group.id,
                'product_id': product.id,
                'product_qty': missing_qty,
                'product_uom_id': product.uom_id.id,
            }
            temp = Line.new(vals)
            # Un vendedor puede preparar el encargo sin tener permisos de MRP/LdM.
            # Si además es usuario de Fabricación, precargamos automáticamente la LdM.
            if self.env.user.has_group('mrp.group_mrp_user'):
                temp._onchange_product_id()
            vals.update(temp._convert_to_write(temp._cache))
            vals['group_id'] = group.id
            vals['product_id'] = product.id
            vals['product_qty'] = missing_qty
            vals['product_uom_id'] = product.uom_id.id
            vals_list.append(vals)
        Line.create(vals_list)
        return group

    def action_esi_prepare_production_group(self):
        self.ensure_one()
        if not self.esi_production_manager_id:
            raise UserError(_('Seleccione el Encargado de producción antes de preparar los faltantes.'))

        existing = self.esi_production_group_ids.filtered(lambda g: g.state in ('draft', 'orders'))[:1]
        if existing:
            # Si aún no se crearon OF, recalculamos el faltante con el stock actual
            # y con las cantidades vigentes del pedido antes de volver a abrirlo.
            if existing.state == 'draft' and not existing.production_ids:
                existing.line_ids.unlink()
                self._esi_fill_production_group_shortages(existing)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Grupo de producción'),
                'res_model': 'esi.production.group',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        group = self.env['esi.production.group'].create({
            'origin': self.name,
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'salesperson_id': self.user_id.id,
            'production_manager_id': self.esi_production_manager_id.id,
            'company_id': self.company_id.id,
        })
        try:
            self._esi_fill_production_group_shortages(group)
        except Exception:
            group.unlink()
            raise
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grupo de producción por faltantes'),
            'res_model': 'esi.production.group',
            'res_id': group.id,
            'view_mode': 'form',
            'target': 'current',
        }
