# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    esi_variant_info = fields.Char(string='Variante (Talla / Color)', compute='_compute_esi_variant_info')
    esi_analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Cuenta analítica de producción',
        help='Centro de costo/analítica de esta orden de fabricación.'
    )
    esi_destajo_ids = fields.One2many('esi.calzado.destajo', 'production_id', string='Destajos')
    esi_destajo_count = fields.Integer(string='Destajos', compute='_compute_esi_summary')
    esi_missing_line_count = fields.Integer(string='Faltantes', compute='_compute_esi_summary')
    esi_account_move_count = fields.Integer(string='Asientos', compute='_compute_esi_account_moves')
    esi_material_cost = fields.Monetary(
        string='Costo materiales estimado', compute='_compute_esi_summary', currency_field='currency_id'
    )
    esi_destajo_cost = fields.Monetary(
        string='Costo destajos', compute='_compute_esi_summary', currency_field='currency_id'
    )
    esi_destajo_confirmed_cost = fields.Monetary(
        string='Destajos valorizados', compute='_compute_esi_summary', currency_field='currency_id'
    )
    esi_missing_cost = fields.Monetary(
        string='Costo materiales faltantes', compute='_compute_esi_summary', currency_field='currency_id'
    )
    esi_other_cost = fields.Monetary(
        string='Otros costos estimados', currency_field='currency_id', default=0.0,
        help='Solo informativo en esta versión. No se capitaliza en la valoración automática.'
    )
    esi_total_estimated_cost = fields.Monetary(
        string='Costo total estimado', compute='_compute_esi_summary', currency_field='currency_id'
    )
    esi_unit_estimated_cost = fields.Monetary(
        string='Costo estimado / unidad', compute='_compute_esi_summary', currency_field='currency_id'
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id_esi_analytic(self):
        if self.product_id and self.product_id.product_tmpl_id.esi_production_analytic_account_id:
            self.esi_analytic_account_id = self.product_id.product_tmpl_id.esi_production_analytic_account_id

    @api.depends('product_id', 'product_id.product_template_attribute_value_ids')
    def _compute_esi_variant_info(self):
        for production in self:
            values = production.product_id.product_template_attribute_value_ids
            production.esi_variant_info = ' | '.join(
                '%s: %s' % (value.attribute_id.name, value.name) for value in values
            ) if values else ''

    @api.depends(
        'move_raw_ids.product_uom_qty', 'move_raw_ids.product_id.standard_price',
        'move_raw_ids.location_id', 'move_raw_ids.reserved_availability',
        'move_raw_ids.esi_cost_snapshot', 'move_raw_ids.esi_cost_locked',
        'esi_destajo_ids.amount', 'esi_destajo_ids.state', 'esi_other_cost', 'product_qty'
    )
    def _compute_esi_summary(self):
        for production in self:
            material_cost = sum(production.move_raw_ids.mapped('esi_total_material_cost'))
            missing_cost = sum(production.move_raw_ids.mapped('esi_missing_cost'))
            all_destajo = sum(production.esi_destajo_ids.mapped('amount'))
            confirmed_destajo = sum(production.esi_destajo_ids.filtered(
                lambda d: d.state in ('confirmed', 'paid')
            ).mapped('amount'))
            total = material_cost + all_destajo + (production.esi_other_cost or 0.0)
            production.esi_destajo_count = len(production.esi_destajo_ids)
            production.esi_missing_line_count = len(
                production.move_raw_ids.filtered(lambda m: m.esi_missing_qty > 0.000001)
            )
            production.esi_material_cost = material_cost
            production.esi_missing_cost = missing_cost
            production.esi_destajo_cost = all_destajo
            production.esi_destajo_confirmed_cost = confirmed_destajo
            production.esi_total_estimated_cost = total
            production.esi_unit_estimated_cost = total / production.product_qty if production.product_qty else 0.0

    def _esi_get_account_moves(self):
        self.ensure_one()
        stock_moves = (self.move_raw_ids | self.move_finished_ids).mapped('account_move_ids')
        destajo_moves = self.esi_destajo_ids.mapped('account_move_id')
        return stock_moves | destajo_moves

    @api.depends(
        'move_raw_ids.account_move_ids', 'move_finished_ids.account_move_ids',
        'esi_destajo_ids.account_move_id'
    )
    def _compute_esi_account_moves(self):
        for production in self:
            production.esi_account_move_count = len(production._esi_get_account_moves())

    def action_view_esi_destajos(self):
        self.ensure_one()
        action = self.env.ref('esi_calzados_v13.action_esi_calzado_destajo').read()[0]
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {
            'default_production_id': self.id,
            'default_uom_id': self.product_uom_id.id,
        }
        return action

    def action_view_esi_account_moves(self):
        self.ensure_one()
        moves = self._esi_get_account_moves()
        return {
            'name': _('Asientos contables de producción'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
            'context': {'create': False},
        }

    def action_esi_refresh_material_costs(self):
        self.mapped('move_raw_ids').esi_capture_current_cost(force=True)
        return True

    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        self.mapped('move_raw_ids').esi_capture_current_cost(force=False)
        for production in self:
            if not production.esi_analytic_account_id and production.product_id:
                analytic = production.product_id.product_tmpl_id.esi_production_analytic_account_id
                if analytic:
                    production.esi_analytic_account_id = analytic.id
        return res

    def _esi_validate_automatic_valuation(self):
        for production in self:
            if production.product_id.type == 'product' and production.product_id.categ_id.property_valuation != 'real_time':
                raise UserError(_(
                    'La valoración del producto terminado %s debe estar configurada como Automática antes de finalizar la OF.'
                ) % production.product_id.display_name)
            raw_products = production.move_raw_ids.filtered(lambda m: m.product_id.type == 'product').mapped('product_id')
            not_real_time = raw_products.filtered(lambda p: p.categ_id.property_valuation != 'real_time')
            if not_real_time:
                raise UserError(_(
                    'La valoración debe ser Automática para las materias primas de esta OF. Revise: %s'
                ) % ', '.join(not_real_time.mapped('display_name')))
            if not production.company_id.esi_wip_account_id:
                raise UserError(_('Configure la cuenta ESI de Producción en Proceso en la compañía.'))
            production_location = production.production_location_id
            if production_location and (
                production_location.valuation_in_account_id != production.company_id.esi_wip_account_id
                or production_location.valuation_out_account_id != production.company_id.esi_wip_account_id
            ):
                raise UserError(_(
                    'La ubicación virtual de Producción debe usar la cuenta %s como cuenta de valoración de entrada y salida.'
                ) % production.company_id.esi_wip_account_id.display_name)
        return True

    def button_mark_done(self):
        # El costo de destajos confirmado se capitaliza con el mecanismo estándar de mrp_account.extra_cost.
        # No se usan tiempos: solo cantidad x tarifa registrada en destajos.
        self._esi_validate_automatic_valuation()
        for production in self:
            drafts = production.esi_destajo_ids.filtered(lambda d: d.state == 'draft')
            if drafts:
                raise UserError(_(
                    'La OF %s tiene destajos en borrador. Confírmelos o elimínelos antes de finalizar '
                    'para que la valoración automática sea consistente.'
                ) % production.name)
            if 'extra_cost' in production._fields:
                qty = production.product_qty or 0.0
                production.extra_cost = (production.esi_destajo_confirmed_cost / qty) if qty else 0.0
        return super(MrpProduction, self).button_mark_done()

    def action_esi_open_purchase_wizard(self):
        self.ensure_one()
        return {
            'name': _('Materiales faltantes / Preparar RFQ'),
            'type': 'ir.actions.act_window',
            'res_model': 'esi.calzado.purchase.request.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('esi_calzados_v13.view_esi_calzado_purchase_request_wizard').id,
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'active_id': self.id,
                'active_model': 'mrp.production'
            },
        }

    def esi_get_shortage_moves(self):
        self.ensure_one()
        return self.move_raw_ids.filtered(lambda m: m.esi_missing_qty > 0.000001)
