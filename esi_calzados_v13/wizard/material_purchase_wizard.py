# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EsiCalzadoPurchaseRequestWizard(models.TransientModel):
    _name = 'esi.calzado.purchase.request.wizard'
    _description = 'ESI - Materiales faltantes para compra'

    production_id = fields.Many2one('mrp.production', string='Orden de fabricación', required=True)
    line_ids = fields.One2many('esi.calzado.purchase.request.wizard.line', 'wizard_id', string='Materiales faltantes')
    currency_id = fields.Many2one(related='production_id.company_id.currency_id', readonly=True)
    total_estimated = fields.Monetary(string='Total estimado', compute='_compute_total', currency_field='currency_id')

    @api.model
    def default_get(self, fields_list):
        vals = super(EsiCalzadoPurchaseRequestWizard, self).default_get(fields_list)
        production = self.env['mrp.production'].browse(
            self.env.context.get('default_production_id') or self.env.context.get('active_id')
        )
        if production:
            vals['production_id'] = production.id
            lines = []
            for move in production.esi_get_shortage_moves():
                seller = move.product_id._select_seller(
                    quantity=move.esi_missing_qty or 1.0,
                    date=fields.Date.today(),
                    uom_id=move.product_uom,
                )
                vendor = seller.name if seller else (move.product_id.seller_ids[:1].name if move.product_id.seller_ids else False)
                lines.append((0, 0, {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'uom_id': move.product_uom.id,
                    'required_qty': move.esi_total_required,
                    'available_qty': move.esi_available_qty,
                    'missing_qty': move.esi_missing_qty,
                    'vendor_id': vendor.id if vendor else False,
                    'unit_price': move.esi_purchase_unit_cost,
                    'selected': True,
                }))
            vals['line_ids'] = lines
        return vals

    @api.depends('line_ids.selected', 'line_ids.subtotal')
    def _compute_total(self):
        for wizard in self:
            wizard.total_estimated = sum(wizard.line_ids.filtered('selected').mapped('subtotal'))

    def action_create_rfqs(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.selected and l.missing_qty > 0)
        if not lines:
            raise UserError(_('No hay líneas seleccionadas con faltantes.'))
        if any(not line.vendor_id for line in lines):
            raise UserError(_('Asigne un proveedor a todas las líneas seleccionadas.'))

        groups = defaultdict(lambda: self.env['esi.calzado.purchase.request.wizard.line'])
        for line in lines:
            groups[line.vendor_id] |= line

        purchase_orders = self.env['purchase.order']
        for vendor, vendor_lines in groups.items():
            po_vals = {
                'partner_id': vendor.id,
                'origin': self.production_id.name,
                'company_id': self.production_id.company_id.id,
            }
            # Compatibilidad opcional con ESI Stores: no crea dependencia dura.
            PurchaseOrder = self.env['purchase.order']
            warehouse = self.production_id.picking_type_id.warehouse_id
            if warehouse and 'picking_type_id' in PurchaseOrder._fields and warehouse.in_type_id:
                po_vals['picking_type_id'] = warehouse.in_type_id.id
            if warehouse and 'store_id' in PurchaseOrder._fields and 'store_id' in warehouse._fields and warehouse.store_id:
                po_vals['store_id'] = warehouse.store_id.id
            po = PurchaseOrder.create(po_vals)
            for line in vendor_lines:
                self.env['purchase.order.line'].create({
                    'order_id': po.id,
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_qty': line.missing_qty,
                    'product_uom': line.uom_id.id,
                    'price_unit': line.unit_price,
                    'date_planned': fields.Datetime.now(),
                })
            purchase_orders |= po

        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitudes de presupuesto creadas'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_orders.ids)],
        }


class EsiCalzadoPurchaseRequestWizardLine(models.TransientModel):
    _name = 'esi.calzado.purchase.request.wizard.line'
    _description = 'ESI - Línea faltante para compra'

    wizard_id = fields.Many2one('esi.calzado.purchase.request.wizard', required=True, ondelete='cascade')
    selected = fields.Boolean(string='Comprar', default=True)
    move_id = fields.Many2one('stock.move', string='Movimiento')
    product_id = fields.Many2one('product.product', string='Material', required=True)
    uom_id = fields.Many2one('uom.uom', string='UdM', required=True)
    required_qty = fields.Float(string='Requerido', digits='Product Unit of Measure')
    available_qty = fields.Float(string='Disponible', digits='Product Unit of Measure')
    missing_qty = fields.Float(string='Faltante', digits='Product Unit of Measure')
    vendor_id = fields.Many2one('res.partner', string='Proveedor', domain="[('supplier_rank','>',0)]")
    unit_price = fields.Float(string='Precio estimado', digits='Product Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', digits='Product Price')

    @api.depends('missing_qty', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.missing_qty or 0.0) * (line.unit_price or 0.0)
