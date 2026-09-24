# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EsiCalzadoDestajoActividad(models.Model):
    _name = 'esi.calzado.destajo.actividad'
    _description = 'Actividad de destajo de calzado'
    _order = 'sequence, name'

    name = fields.Char(string='Actividad', required=True)
    code = fields.Char(string='Código')
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(default=True)
    default_unit_price = fields.Monetary(
        string='Tarifa sugerida', currency_field='currency_id', default=0.0
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    expense_account_id = fields.Many2one(
        'account.account', string='Cuenta de gasto',
        domain="[('company_id', '=', company_id)]",
        help='Cuenta de gasto de sueldos/extras que se debita al confirmar este tipo de destajo. '
             'El destajo ya no se capitaliza en el costo de la orden de producción.'
    )
    notes = fields.Text(string='Observaciones')


class EsiCalzadoDestajo(models.Model):
    _name = 'esi.calzado.destajo'
    _description = 'Destajo de calzado (gasto independiente)'
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', default='Nuevo', copy=False, readonly=True)
    # Campo legado para mantener compatibilidad con registros existentes. Ya no se usa
    # en formularios, reportes ni en el costo/cierre de las órdenes de producción.
    production_id = fields.Many2one(
        'mrp.production', string='Orden de fabricación (histórico)', required=False,
        ondelete='set null', index=True, copy=False
    )
    product_id = fields.Many2one(
        'product.product', string='Producto / Línea (opcional)',
        help='Referencia informativa. No vincula el destajo con una orden de producción.'
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Cuenta analítica (opcional)',
        help='Centro de costo analítico del gasto de destajo, si corresponde.'
    )
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Operador / Destajista', required=True,
        help='Persona que realizó la actividad a destajo.'
    )
    activity_id = fields.Many2one(
        'esi.calzado.destajo.actividad', string='Actividad realizada', required=True,
        domain="[('company_id', '=', company_id)]"
    )
    description = fields.Char(string='Detalle')
    quantity = fields.Float(
        string='Cantidad realizada', default=1.0, required=True,
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one('uom.uom', string='Unidad de medida', required=True)
    unit_price = fields.Monetary(string='Tarifa por unidad', required=True, default=0.0)
    amount = fields.Monetary(string='Importe', compute='_compute_amount', store=True)
    expense_account_id = fields.Many2one(
        'account.account', string='Cuenta de gasto',
        domain="[('company_id', '=', company_id)]",
        help='Gasto de sueldos/extras. No afecta la valoración del producto terminado.'
    )
    state = fields.Selection(
        [('draft', 'Borrador'), ('confirmed', 'Confirmado'), ('paid', 'Pagado')],
        string='Estado', default='draft', required=True
    )
    account_move_id = fields.Many2one('account.move', string='Asiento contable', readonly=True, copy=False)
    notes = fields.Text(string='Observaciones')

    @api.constrains('quantity', 'unit_price')
    def _check_values(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_('La cantidad del destajo debe ser mayor a cero.'))
            if rec.unit_price < 0:
                raise ValidationError(_('La tarifa del destajo no puede ser negativa.'))

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if self.activity_id:
            if not self.unit_price:
                self.unit_price = self.activity_id.default_unit_price
            if not self.expense_account_id:
                self.expense_account_id = self.activity_id.expense_account_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.uom_id:
            self.uom_id = self.product_id.uom_id

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.quantity or 0.0) * (rec.unit_price or 0.0)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('esi.calzado.destajo') or _('Nuevo')
        if vals.get('activity_id') and not vals.get('expense_account_id'):
            activity = self.env['esi.calzado.destajo.actividad'].browse(vals['activity_id'])
            vals['expense_account_id'] = activity.expense_account_id.id or False
        if vals.get('product_id') and not vals.get('uom_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['uom_id'] = product.uom_id.id
        return super(EsiCalzadoDestajo, self).create(vals)

    def write(self, vals):
        protected = {'partner_id', 'activity_id', 'quantity', 'uom_id', 'unit_price', 'date', 'expense_account_id'}
        if protected.intersection(vals.keys()) and any(rec.state != 'draft' for rec in self):
            raise UserError(_('No se puede modificar un destajo confirmado.'))
        return super(EsiCalzadoDestajo, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.account_move_id:
                raise UserError(_('No se puede eliminar un destajo que ya tiene asiento contable.'))
        return super(EsiCalzadoDestajo, self).unlink()

    def _create_account_move(self):
        self.ensure_one()
        company = self.company_id
        expense_account = self.expense_account_id or self.activity_id.expense_account_id
        if not expense_account:
            raise UserError(_(
                'Configure una Cuenta de gasto en la actividad %s o en el propio destajo.'
            ) % self.activity_id.display_name)
        if not company.esi_piecework_payable_account_id:
            raise UserError(_('Configure la cuenta ESI de Destajos por Pagar en la compañía.'))
        if not company.esi_production_journal_id:
            raise UserError(_('Configure el diario ESI de Producción/Gastos en la compañía.'))
        if self.account_move_id:
            return self.account_move_id

        line_name = '%s - %s - %s' % (
            self.name,
            self.activity_id.name,
            self.partner_id.display_name,
        )
        debit_vals = {
            'name': line_name,
            'account_id': expense_account.id,
            'debit': self.amount,
            'credit': 0.0,
            'partner_id': self.partner_id.id,
        }
        if self.analytic_account_id:
            debit_vals['analytic_account_id'] = self.analytic_account_id.id

        move = self.env['account.move'].create({
            'date': self.date,
            'journal_id': company.esi_production_journal_id.id,
            'ref': 'Gasto destajo %s' % self.name,
            'type': 'entry',
            'line_ids': [
                (0, 0, debit_vals),
                (0, 0, {
                    'name': line_name,
                    'account_id': company.esi_piecework_payable_account_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': self.partner_id.id,
                }),
            ],
        })
        move.post()
        self.account_move_id = move.id
        return move

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec._create_account_move()
            rec.state = 'confirmed'
        return True

    def action_paid(self):
        self.filtered(lambda r: r.state == 'confirmed').write({'state': 'paid'})
        return True

    def action_view_account_move(self):
        self.ensure_one()
        if not self.account_move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asiento del destajo'),
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
