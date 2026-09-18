# -*- coding: utf-8 -*-
# ESI - Especialistas en Sistemas Integrados

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AutomatedSaleOrder(models.Model):
    _name = 'automated.sale'
    _description = 'Tipo de Venta'
    _order = 'sequence, name, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id,
    )
    st_almacen = fields.Many2one('stock.warehouse', string='Almacén', required=True)
    st_secuencia_quotation = fields.Many2one('ir.sequence', string='Secuencia Cotización')
    st_secuencia = fields.Many2one('ir.sequence', string='Secuencia Venta')
    sales_journal = fields.Many2one('account.journal', string='Diario de Ventas', required=True)
    payment_journal = fields.Many2one('account.journal', string='Diario de Pago', required=True)
    validation_picking = fields.Boolean(string='Validar Entrega', default=False)
    validate_invoice = fields.Boolean(string='Publicar Factura', default=True)

    @api.onchange('company_id')
    def _onchange_company_id_esi(self):
        for rec in self:
            if rec.st_almacen and rec.st_almacen.company_id != rec.company_id:
                rec.st_almacen = False
            if rec.sales_journal and rec.sales_journal.company_id != rec.company_id:
                rec.sales_journal = False
            if rec.payment_journal and rec.payment_journal.company_id != rec.company_id:
                rec.payment_journal = False

    @api.constrains(
        'company_id', 'st_almacen', 'st_secuencia', 'st_secuencia_quotation',
        'sales_journal', 'payment_journal'
    )
    def _check_sale_type_configuration(self):
        for rec in self:
            if rec.st_almacen and rec.st_almacen.company_id != rec.company_id:
                raise ValidationError(_('El almacén no pertenece a la compañía seleccionada.'))
            if rec.sales_journal and rec.sales_journal.company_id != rec.company_id:
                raise ValidationError(_('El Diario de Ventas no pertenece a la compañía seleccionada.'))
            if rec.sales_journal and rec.sales_journal.type != 'sale':
                raise ValidationError(_('El Diario de Ventas debe ser de tipo Ventas.'))
            if rec.payment_journal and rec.payment_journal.company_id != rec.company_id:
                raise ValidationError(_('El Diario de Pago no pertenece a la compañía seleccionada.'))
            if rec.payment_journal and rec.payment_journal.type not in ('bank', 'cash'):
                raise ValidationError(_('El Diario de Pago debe ser de tipo Banco o Efectivo.'))
            for sequence in (rec.st_secuencia_quotation, rec.st_secuencia):
                if sequence and sequence.company_id and sequence.company_id != rec.company_id:
                    raise ValidationError(_('La secuencia no pertenece a la compañía seleccionada.'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    work_process_order_id = fields.Many2one(
        'automated.sale', string='Tipo de Venta', copy=True,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
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
    def _esi_sale_type_vals(self, sale_type):
        return {'warehouse_id': sale_type.st_almacen.id or False}

    @api.onchange('work_process_order_id')
    def _onchange_work_process_order_id_esi(self):
        for order in self:
            if order.work_process_order_id:
                order.warehouse_id = order.work_process_order_id.st_almacen

    @api.model
    def create(self, vals):
        vals = dict(vals)
        type_id = vals.get('work_process_order_id')
        if type_id:
            sale_type = self.env['automated.sale'].browse(type_id).exists()
            if sale_type:
                vals.update(self._esi_sale_type_vals(sale_type))
                if not vals.get('name') or vals.get('name') in ('New', _('New')):
                    name = self._esi_next_sequence(
                        sale_type.st_secuencia_quotation,
                        vals.get('date_order'),
                        sale_type.company_id,
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
                sale_type = self.env['automated.sale'].browse(type_id).exists()
                if sale_type:
                    current_vals.update(self._esi_sale_type_vals(sale_type))
                    if order.state in ('draft', 'sent') and order.work_process_order_id != sale_type:
                        name = self._esi_next_sequence(
                            sale_type.st_secuencia_quotation,
                            order.date_order,
                            sale_type.company_id,
                        )
                        if name:
                            current_vals['name'] = name
            result = super(SaleOrder, order).write(current_vals) and result
        return result

    def _esi_validate_sale_type(self):
        for order in self:
            sale_type = order.work_process_order_id
            if not sale_type:
                raise UserError(_('Debe seleccionar un Tipo de Venta antes de confirmar.'))
            if not sale_type.st_almacen:
                raise UserError(_('El Tipo de Venta debe tener un Almacén configurado.'))
            if not sale_type.st_secuencia:
                raise UserError(_('El Tipo de Venta debe tener una Secuencia Venta configurada.'))
            if not sale_type.sales_journal:
                raise UserError(_('El Tipo de Venta debe tener un Diario de Ventas configurado.'))
            if not sale_type.payment_journal:
                raise UserError(_('El Tipo de Venta debe tener un Diario de Pago configurado.'))
            if sale_type.company_id != order.company_id:
                raise UserError(_('El Tipo de Venta pertenece a otra compañía.'))
        return True

    def _esi_validate_delivery(self):
        self.ensure_one()
        pickings = self.sudo().picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel') and p.picking_type_id.code == 'outgoing'
        )
        for picking in pickings:
            picking.action_assign()
            tracked = picking.move_lines.filtered(
                lambda m: m.product_id.tracking in ('lot', 'serial') and m.product_uom_qty > 0
            )
            if tracked:
                self.message_post(body=_(
                    'ESI: la entrega quedó pendiente porque contiene productos con lote o número de serie. '
                    'Complete el detalle de la transferencia y valídela manualmente.'
                ))
                continue
            for move in picking.move_lines.filtered(lambda m: m.state not in ('done', 'cancel')):
                move.quantity_done = move.product_uom_qty
            picking.button_validate()

    def _esi_create_and_post_invoice(self):
        self.ensure_one()
        order = self.sudo()
        invoices_before = order.invoice_ids
        invoiceable_lines = order.order_line.filtered(
            lambda l: not l.display_type and l.qty_to_invoice > 0
        )
        if not invoices_before and invoiceable_lines:
            order._create_invoices()
        invoices = order.invoice_ids.filtered(lambda inv: inv.type == 'out_invoice')
        draft_invoices = invoices.filtered(lambda inv: inv.state == 'draft')
        if draft_invoices and self.work_process_order_id.sales_journal:
            draft_invoices.write({'journal_id': self.work_process_order_id.sales_journal.id})
        if self.work_process_order_id.validate_invoice:
            for invoice in draft_invoices:
                invoice.action_post()
        if not invoices and not invoiceable_lines:
            self.message_post(body=_(
                'ESI: todavía no hay cantidades facturables. Si el producto factura por cantidades '
                'entregadas, la factura podrá generarse después de validar la entrega.'
            ))

    def action_confirm(self):
        self._esi_validate_sale_type()
        for order in self:
            sale_type = order.work_process_order_id
            values = self._esi_sale_type_vals(sale_type)
            name = self._esi_next_sequence(
                sale_type.st_secuencia,
                order.date_order,
                sale_type.company_id,
            )
            if name:
                values['name'] = name
            super(SaleOrder, order).write(values)
        result = super().action_confirm()
        for order in self:
            if order.work_process_order_id.validation_picking:
                order._esi_validate_delivery()
            order._esi_create_and_post_invoice()
        return result

    def _compute_esi_can_register_payment(self):
        for order in self:
            invoices = order.sudo().invoice_ids.filtered(
                lambda inv: inv.type == 'out_invoice' and inv.state == 'posted' and inv.amount_residual > 0
            )
            order.esi_can_register_payment = bool(invoices)

    def action_open_esi_payment_wizard(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        if self.state not in ('sale', 'done'):
            raise UserError(_('Primero debe confirmar la venta.'))
        invoices = self.sudo().invoice_ids.filtered(
            lambda inv: inv.type == 'out_invoice' and inv.state == 'posted' and inv.amount_residual > 0
        )
        if not invoices:
            raise UserError(_('No existe una factura publicada con saldo pendiente para registrar el pago.'))
        return {
            'name': _('Registrar Pago de Venta'),
            'type': 'ir.actions.act_window',
            'res_model': 'esi.sale.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, default_sale_order_id=self.id),
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    esi_sale_order_id = fields.Many2one('sale.order', string='Venta ESI', readonly=True, copy=False)
    esi_sale_registered_by_id = fields.Many2one('res.users', string='Registrado por', readonly=True, copy=False)
