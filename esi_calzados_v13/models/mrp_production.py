# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


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

    # Producción en Proceso (WIP) provisional. Odoo 13 contabiliza la valoración
    # definitiva al publicar inventario / cerrar la OF. Estos campos permiten
    # que el Balance muestre el material ya registrado con el botón Producir
    # mientras la OF todavía está En progreso / Por cerrar.
    esi_wip_material_move_id = fields.Many2one(
        'account.move', string='Asiento WIP materiales', readonly=True, copy=False
    )
    esi_wip_material_amount = fields.Monetary(
        string='Materiales en Producción en Proceso', currency_field='currency_id',
        readonly=True, copy=False, default=0.0
    )
    esi_wip_registered = fields.Boolean(
        string='WIP registrado', readonly=True, copy=False, default=False
    )
    esi_wip_registered_date = fields.Date(
        string='Fecha registro WIP', readonly=True, copy=False
    )

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
        wip_moves = self.env['account.move'].search([('esi_mrp_production_id', '=', self.id)])
        return stock_moves | destajo_moves | wip_moves

    @api.depends(
        'move_raw_ids.account_move_ids', 'move_finished_ids.account_move_ids',
        'esi_destajo_ids.account_move_id', 'esi_wip_material_move_id'
    )
    def _compute_esi_account_moves(self):
        for production in self:
            production.esi_account_move_count = len(production._esi_get_account_moves())

    def _esi_get_raw_valuation_account(self, move):
        """Cuenta de valoración del material respetando propiedades por compañía."""
        self.ensure_one()
        product = move.product_id.with_context(force_company=self.company_id.id)
        category = product.categ_id.with_context(force_company=self.company_id.id)
        return category.property_stock_valuation_account_id

    def _esi_reverse_wip_provisional(self):
        """Revierte el asiento provisional de materiales en proceso, si existe."""
        for production in self:
            move = production.esi_wip_material_move_id
            if not move:
                production.write({
                    'esi_wip_material_amount': 0.0,
                    'esi_wip_registered': False,
                    'esi_wip_registered_date': False,
                })
                continue
            if move.state == 'posted':
                move = move.sudo()
                reverse = move._reverse_moves([{
                    'date': fields.Date.context_today(production),
                    'ref': _('Reversión WIP provisional %s') % production.name,
                }], cancel=False)
                reverse.write({
                    'esi_mrp_production_id': production.id,
                    'esi_wip_kind': 'reversal',
                })
                reverse.post()
            elif move.state == 'draft':
                move.sudo().unlink()
            production.write({
                'esi_wip_material_move_id': False,
                'esi_wip_material_amount': 0.0,
                'esi_wip_registered': False,
                'esi_wip_registered_date': False,
            })
        return True

    def _esi_sync_wip_provisional(self):
        """Reclasifica materiales registrados con *Producir* hacia WIP.

        Este asiento es deliberadamente provisional: al publicar inventario o
        cerrar la OF se revierte antes de que Odoo genere la valoración estándar.
        Así no existe duplicidad contable y la cuenta 154000 puede mostrar saldo
        mientras la OF está En progreso / Por cerrar.
        """
        for production in self:
            if production.state in ('draft', 'done', 'cancel'):
                production._esi_reverse_wip_provisional()
                continue

            company = production.company_id
            # Si una empresa aún no configuró ESI WIP, no bloqueamos el botón
            # estándar Producir. La validación definitiva seguirá ocurriendo al cerrar.
            if not company.esi_wip_account_id or not company.esi_production_journal_id:
                production._esi_reverse_wip_provisional()
                continue

            # Sustituir el asiento anterior por uno recalculado evita duplicar WIP
            # al usar varias veces Producir / Continuar producción.
            production._esi_reverse_wip_provisional()

            amounts_by_account = defaultdict(float)
            total = 0.0
            for raw_move in production.move_raw_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel') and m.product_id.type == 'product'):
                qty = raw_move.quantity_done or 0.0
                if float_is_zero(qty, precision_rounding=raw_move.product_uom.rounding):
                    continue
                # Mantener costo histórico de la OF cuando ya fue capturado.
                unit_cost = raw_move.esi_cost_snapshot if raw_move.esi_cost_locked else raw_move._esi_get_live_unit_cost()
                amount = company.currency_id.round(qty * unit_cost)
                if company.currency_id.is_zero(amount):
                    continue
                valuation_account = production._esi_get_raw_valuation_account(raw_move)
                if not valuation_account:
                    raise UserError(_(
                        'El material %s no tiene Cuenta de valoración de inventario en su categoría.'
                    ) % raw_move.product_id.display_name)
                amounts_by_account[valuation_account.id] += amount
                total += amount

            total = company.currency_id.round(total)
            if company.currency_id.is_zero(total):
                continue

            debit_vals = {
                'name': _('Materiales en proceso - %s') % production.name,
                'account_id': company.esi_wip_account_id.id,
                'debit': total,
                'credit': 0.0,
            }
            if production.esi_analytic_account_id:
                debit_vals['analytic_account_id'] = production.esi_analytic_account_id.id

            line_ids = [(0, 0, debit_vals)]
            for account_id, amount in amounts_by_account.items():
                amount = company.currency_id.round(amount)
                if company.currency_id.is_zero(amount):
                    continue
                line_ids.append((0, 0, {
                    'name': _('Salida temporal a producción - %s') % production.name,
                    'account_id': account_id,
                    'debit': 0.0,
                    'credit': amount,
                }))

            account_move = self.env['account.move'].sudo().create({
                'date': fields.Date.context_today(production),
                'journal_id': company.esi_production_journal_id.id,
                'ref': _('WIP provisional materiales / %s') % production.name,
                'type': 'entry',
                'esi_mrp_production_id': production.id,
                'esi_wip_kind': 'material',
                'line_ids': line_ids,
            })
            account_move.post()
            production.write({
                'esi_wip_material_move_id': account_move.id,
                'esi_wip_material_amount': total,
                'esi_wip_registered': True,
                'esi_wip_registered_date': fields.Date.context_today(production),
            })
        return True

    def action_esi_sync_wip_provisional(self):
        self._esi_sync_wip_provisional()
        return True

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

    def action_cancel(self):
        # Si la OF se cancela antes de cerrar, no debe quedar saldo provisional
        # en Producción en Proceso por materiales que finalmente no se fabricarán.
        self._esi_reverse_wip_provisional()
        return super(MrpProduction, self).action_cancel()

    def post_inventory(self):
        # Antes de que Odoo publique la valoración real, anulamos la
        # reclasificación provisional para evitar duplicar Materia Prima -> WIP.
        self._esi_reverse_wip_provisional()
        return super(MrpProduction, self).post_inventory()

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
