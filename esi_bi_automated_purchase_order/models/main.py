# -*- coding: utf-8 -*-
# ESI - Especialistas en Sistemas Integrados

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AutomatedPurchaseOrder(models.Model):
    _name = 'automated.purchase'
    _description = 'Tipo de Compra'
    _order = 'sequence, name, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.user.company_id,
    )
    st_almacen = fields.Many2one('stock.warehouse', string='Almacén')
    st_entregar_a = fields.Many2one('stock.picking.type', string='Entregar a')
    st_secuencia_quotation = fields.Many2one('ir.sequence', string='Secuencia Solicitud')
    st_secuencia = fields.Many2one('ir.sequence', string='Secuencia Compra')
    purchase_journal = fields.Many2one('account.journal', string='Diario de Compras')
    payment_journal = fields.Many2one('account.journal', string='Diario de Pago')
    validation_picking = fields.Boolean(string='Validar Recepción', default=False)
    validate_invoice = fields.Boolean(string='Publicar Factura', default=True)
    allow_payment_from_purchase = fields.Boolean(
        string='Realizar Pagos desde Compras', default=True
    )

    @api.onchange('company_id')
    def _onchange_company_id_esi(self):
        for rec in self:
            if rec.st_almacen and rec.st_almacen.company_id != rec.company_id:
                rec.st_almacen = False
                rec.st_entregar_a = False
            if rec.purchase_journal and rec.purchase_journal.company_id != rec.company_id:
                rec.purchase_journal = False
            if rec.payment_journal and rec.payment_journal.company_id != rec.company_id:
                rec.payment_journal = False

    @api.onchange('st_almacen')
    def _onchange_st_almacen_esi(self):
        for rec in self:
            rec.st_entregar_a = rec.st_almacen.in_type_id if rec.st_almacen else False

    @api.model
    def create(self, vals):
        vals = dict(vals)
        if vals.get('st_almacen'):
            warehouse = self.env['stock.warehouse'].browse(vals['st_almacen'])
            vals['st_entregar_a'] = warehouse.in_type_id.id or False
        return super().create(vals)

    def write(self, vals):
        vals = dict(vals)
        if 'st_almacen' in vals:
            if vals.get('st_almacen'):
                warehouse = self.env['stock.warehouse'].browse(vals['st_almacen'])
                vals['st_entregar_a'] = warehouse.in_type_id.id or False
            else:
                vals['st_entregar_a'] = False
        return super().write(vals)

    @api.constrains(
        'company_id', 'st_almacen', 'st_secuencia', 'st_secuencia_quotation',
        'purchase_journal', 'payment_journal'
    )
    def _check_purchase_type_configuration(self):
        for rec in self:
            if rec.st_almacen and rec.st_almacen.company_id != rec.company_id:
                raise ValidationError(_('El almacén no pertenece a la compañía seleccionada.'))
            if rec.purchase_journal and rec.purchase_journal.company_id != rec.company_id:
                raise ValidationError(_('El Diario de Compras no pertenece a la compañía seleccionada.'))
            if rec.purchase_journal and rec.purchase_journal.type != 'purchase':
                raise ValidationError(_('El Diario de Compras debe ser de tipo Compras.'))
            if rec.payment_journal and rec.payment_journal.company_id != rec.company_id:
                raise ValidationError(_('El Diario de Pago no pertenece a la compañía seleccionada.'))
            if rec.payment_journal and rec.payment_journal.type not in ('bank', 'cash'):
                raise ValidationError(_('El Diario de Pago debe ser de tipo Banco o Efectivo.'))
            for sequence in (rec.st_secuencia_quotation, rec.st_secuencia):
                if sequence and sequence.company_id and sequence.company_id != rec.company_id:
                    raise ValidationError(_('La secuencia no pertenece a la compañía seleccionada.'))


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    work_process_order_id = fields.Many2one(
        'automated.purchase', string='Tipo de Compra', copy=True,
        domain="['&', ('active', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    esi_can_register_payment = fields.Boolean(
        string='Puede registrar pago', compute='_compute_esi_can_register_payment'
    )

    @api.model
    def _esi_sequence_date(self, value):
        if not value:
            return False
        if isinstance(value, str):
            value = fields.Datetime.from_string(value)
        return value.date() if hasattr(value, 'date') else value

    @api.model
    def _esi_next_sequence(self, sequence, date_order, company):
        if not sequence:
            return False
        context = dict(self.env.context)
        if company:
            context['force_company'] = company.id
        sequence_date = self._esi_sequence_date(date_order)
        if sequence_date:
            context['ir_sequence_date'] = sequence_date
        return sequence.with_context(context).next_by_id()

    @api.model
    def _esi_purchase_type_vals(self, purchase_type):
        warehouse = purchase_type.st_almacen
        vals = {}
        if warehouse and warehouse.in_type_id:
            vals['picking_type_id'] = warehouse.in_type_id.id
        return vals

    @api.onchange('work_process_order_id')
    def _onchange_work_process_order_id_esi(self):
        for order in self:
            if order.work_process_order_id and order.work_process_order_id.st_almacen:
                order.picking_type_id = order.work_process_order_id.st_almacen.in_type_id

    @api.model
    def create(self, vals):
        vals = dict(vals)
        type_id = vals.get('work_process_order_id')
        if type_id:
            purchase_type = self.env['automated.purchase'].browse(type_id).exists()
            if purchase_type:
                vals.update(self._esi_purchase_type_vals(purchase_type))
                if not vals.get('name') or vals.get('name') in ('New', _('New')):
                    name = self._esi_next_sequence(
                        purchase_type.st_secuencia_quotation,
                        vals.get('date_order'),
                        purchase_type.company_id,
                    )
                    if name:
                        vals['name'] = name
        return super().create(vals)

    def write(self, vals):
        if 'work_process_order_id' not in vals:
            return super().write(vals)
        result = True
        for order in self:
            current_vals = dict(vals)
            type_id = current_vals.get('work_process_order_id')
            if type_id:
                purchase_type = self.env['automated.purchase'].browse(type_id).exists()
                if purchase_type:
                    current_vals.update(self._esi_purchase_type_vals(purchase_type))
                    if order.state in ('draft', 'sent', 'to approve') and order.work_process_order_id != purchase_type:
                        name = self._esi_next_sequence(
                            purchase_type.st_secuencia_quotation,
                            order.date_order,
                            purchase_type.company_id,
                        )
                        if name:
                            current_vals['name'] = name
            result = super(PurchaseOrder, order).write(current_vals) and result
        return result

    def _esi_validate_purchase_type(self):
        for order in self:
            purchase_type = order.work_process_order_id
            if not purchase_type:
                raise UserError(_('Debe seleccionar un Tipo de Compra antes de confirmar.'))
            if purchase_type.company_id and purchase_type.company_id != order.company_id:
                raise UserError(_('El Tipo de Compra pertenece a otra compañía.'))
            if purchase_type.st_almacen and not purchase_type.st_almacen.in_type_id:
                raise UserError(_('El almacén configurado no tiene una operación de Recepciones.'))
        return True

    def _esi_validate_receipt(self):
        self.ensure_one()
        pickings = self.sudo().picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel') and p.picking_type_id.code == 'incoming'
        )
        for picking in pickings:
            picking.action_assign()
            tracked = picking.move_lines.filtered(
                lambda m: m.product_id.tracking in ('lot', 'serial') and m.product_uom_qty > 0
            )
            if tracked:
                self.message_post(body=_(
                    'ESI: la recepción quedó pendiente porque contiene productos con lote o número de serie. '
                    'Complete el detalle de la transferencia y valídela manualmente.'
                ))
                continue
            for move in picking.move_lines.filtered(lambda m: m.state not in ('done', 'cancel')):
                move.quantity_done = move.product_uom_qty
            picking.button_validate()

    def _esi_create_and_post_bill(self):
        self.ensure_one()
        order = self.sudo()
        invoiceable_lines = order.order_line.filtered(
            lambda l: not l.display_type and l.qty_to_invoice > 0
        )
        if not order.invoice_ids and invoiceable_lines:
            order.action_create_invoice()
        invoices = order.invoice_ids.filtered(lambda inv: inv.type == 'in_invoice')
        draft_invoices = invoices.filtered(lambda inv: inv.state == 'draft')
        if draft_invoices and self.work_process_order_id.purchase_journal:
            draft_invoices.write({'journal_id': self.work_process_order_id.purchase_journal.id})
        if self.work_process_order_id.validate_invoice:
            for invoice in draft_invoices:
                invoice.action_post()
        if not invoices and not invoiceable_lines:
            self.message_post(body=_(
                'ESI: todavía no hay cantidades facturables. Si el producto se factura por cantidades '
                'recibidas, la factura podrá generarse después de validar la recepción.'
            ))

    def button_confirm(self):
        self._esi_validate_purchase_type()
        for order in self:
            purchase_type = order.work_process_order_id
            values = self._esi_purchase_type_vals(purchase_type)
            name = self._esi_next_sequence(
                purchase_type.st_secuencia,
                order.date_order,
                purchase_type.company_id,
            )
            if name:
                values['name'] = name
            super(PurchaseOrder, order).write(values)
        result = super().button_confirm()
        for order in self:
            if order.work_process_order_id.validation_picking:
                order._esi_validate_receipt()
            order._esi_create_and_post_bill()
        return result

    def _compute_esi_can_register_payment(self):
        for order in self:
            invoices = order.sudo().invoice_ids.filtered(
                lambda inv: inv.type == 'in_invoice' and inv.state == 'posted' and inv.amount_residual > 0
            )
            purchase_type = order.work_process_order_id
            order.esi_can_register_payment = bool(
                invoices and purchase_type and purchase_type.allow_payment_from_purchase
            )

    def action_open_esi_payment_wizard(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if self.state not in ('purchase', 'done'):
            raise UserError(_('Primero debe confirmar la compra.'))
        purchase_type = self.work_process_order_id
        if not purchase_type or not purchase_type.allow_payment_from_purchase:
            raise UserError(_('El registro de pagos desde Compras está desactivado para este Tipo de Compra.'))
        invoices = self.sudo().invoice_ids.filtered(
            lambda inv: inv.type == 'in_invoice' and inv.state == 'posted' and inv.amount_residual > 0
        )
        if not invoices:
            raise UserError(_('No existe una factura publicada con saldo pendiente para registrar el pago.'))
        return {
            'name': _('Registrar Pago de Compra'),
            'type': 'ir.actions.act_window',
            'res_model': 'esi.purchase.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, default_purchase_order_id=self.id),
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    esi_purchase_order_id = fields.Many2one('purchase.order', string='Compra ESI', readonly=True, copy=False)
    esi_purchase_registered_by_id = fields.Many2one('res.users', string='Registrado por', readonly=True, copy=False)
