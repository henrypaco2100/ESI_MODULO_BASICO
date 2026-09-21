# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    esi_material_group = fields.Selection(
        related='bom_line_id.esi_material_group',
        string='Detalle / Grupo', readonly=True,
    )
    esi_cost_snapshot = fields.Float(
        string='Costo capturado ESI', digits='Product Price', copy=False,
        help='Costo del material capturado para conservar el costo histórico de la OF.'
    )
    esi_cost_locked = fields.Boolean(string='Costo capturado', default=False, copy=False)
    esi_qty_per_unit = fields.Float(
        string='Cant. requerida / unidad', digits='Product Unit of Measure',
        compute='_compute_esi_calzado_values'
    )
    esi_unit_cost = fields.Float(
        string='Costo unitario', digits='Product Price', compute='_compute_esi_calzado_values'
    )
    esi_unit_material_cost = fields.Float(
        string='Costo material / unidad', digits='Product Price', compute='_compute_esi_calzado_values'
    )
    esi_total_required = fields.Float(
        string='Cant. total requerida', digits='Product Unit of Measure', compute='_compute_esi_calzado_values'
    )
    esi_total_material_cost = fields.Float(
        string='Costo total material', digits='Product Price', compute='_compute_esi_calzado_values'
    )
    esi_available_qty = fields.Float(
        string='Disponible p/OF', digits='Product Unit of Measure', compute='_compute_esi_calzado_values',
        help='Disponible en la ubicación origen más lo ya reservado para esta OF.'
    )
    esi_missing_qty = fields.Float(
        string='Faltante', digits='Product Unit of Measure', compute='_compute_esi_calzado_values'
    )
    esi_purchase_unit_cost = fields.Float(
        string='Costo compra estimado', digits='Product Price', compute='_compute_esi_calzado_values'
    )
    esi_missing_cost = fields.Float(
        string='Costo faltante', digits='Product Price', compute='_compute_esi_calzado_values'
    )

    def _esi_get_live_unit_cost(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return 0.0
        company = self.company_id or self.env.company
        product = product.sudo().with_context(force_company=company.id)
        unit_cost = product.standard_price or 0.0
        if self.product_uom and product.uom_id and self.product_uom != product.uom_id:
            if self.product_uom.category_id == product.uom_id.category_id:
                unit_cost = product.uom_id._compute_price(unit_cost, self.product_uom)
        return unit_cost

    def _esi_get_supplier_price(self, quantity=0.0):
        self.ensure_one()
        if not self.product_id:
            return 0.0
        seller = self.product_id._select_seller(
            quantity=quantity or self.product_uom_qty or 1.0,
            date=fields.Date.today(),
            uom_id=self.product_uom,
        )
        if not seller:
            return 0.0
        price = seller.price or 0.0
        if seller.product_uom and self.product_uom and seller.product_uom != self.product_uom:
            if seller.product_uom.category_id == self.product_uom.category_id:
                price = seller.product_uom._compute_price(price, self.product_uom)
        return price

    def esi_capture_current_cost(self, force=False):
        for move in self:
            if force or not move.esi_cost_locked:
                move.write({
                    'esi_cost_snapshot': move._esi_get_live_unit_cost(),
                    'esi_cost_locked': True,
                })
        return True

    @api.depends(
        'product_id', 'product_uom', 'product_uom_qty', 'location_id',
        'reserved_availability', 'state', 'esi_cost_snapshot', 'esi_cost_locked',
        'raw_material_production_id.product_qty', 'product_id.standard_price',
    )
    def _compute_esi_calzado_values(self):
        for move in self:
            product = move.product_id
            production = move.raw_material_production_id
            total_required = move.product_uom_qty or 0.0
            production_qty = production.product_qty if production else 0.0
            qty_per_unit = total_required / production_qty if production_qty else 0.0

            live_cost = move._esi_get_live_unit_cost() if product else 0.0
            unit_cost = move.esi_cost_snapshot if move.esi_cost_locked else live_cost

            available = 0.0
            if product and move.location_id:
                product_ctx = product.with_context(location=move.location_id.id)
                free_qty = product_ctx.free_qty if 'free_qty' in product._fields else product_ctx.qty_available
                if move.product_uom and product.uom_id and move.product_uom != product.uom_id:
                    if move.product_uom.category_id == product.uom_id.category_id:
                        free_qty = product.uom_id._compute_quantity(free_qty, move.product_uom)
                available = max(0.0, free_qty + (move.reserved_availability or 0.0))

            missing = max(0.0, total_required - available)
            supplier_price = move._esi_get_supplier_price(missing) if missing else 0.0
            purchase_unit_cost = supplier_price or unit_cost

            move.esi_qty_per_unit = qty_per_unit
            move.esi_unit_cost = unit_cost
            move.esi_unit_material_cost = qty_per_unit * unit_cost
            move.esi_total_required = total_required
            move.esi_total_material_cost = total_required * unit_cost
            move.esi_available_qty = available
            move.esi_missing_qty = missing
            move.esi_purchase_unit_cost = purchase_unit_cost
            move.esi_missing_cost = missing * purchase_unit_cost

    def esi_get_supplier_name(self):
        self.ensure_one()
        if not self.product_id:
            return ''
        seller = self.product_id._select_seller(
            quantity=self.esi_missing_qty or self.product_uom_qty or 1.0,
            date=fields.Date.today(),
            uom_id=self.product_uom,
        )
        if seller and seller.name:
            return seller.name.display_name
        if self.product_id.seller_ids:
            return self.product_id.seller_ids[0].name.display_name
        return ''

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value,
                                       debit_account_id, credit_account_id, description):
        """Agregar analítica únicamente al débito del consumo de materia prima.

        Esto mantiene un centro de costo de fabricación sin duplicar el costo al ingresar
        el producto terminado.
        """
        res = super(StockMove, self)._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value,
            debit_account_id, credit_account_id, description
        )
        self.ensure_one()
        production = self.raw_material_production_id
        if production and production.esi_analytic_account_id:
            debit_vals = res.get('debit_line_vals')
            if debit_vals is not None:
                debit_vals['analytic_account_id'] = production.esi_analytic_account_id.id
        return res
