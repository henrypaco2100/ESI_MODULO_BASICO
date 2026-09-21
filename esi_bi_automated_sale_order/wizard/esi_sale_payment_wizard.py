# -*- coding: utf-8 -*-
# ESI - Registro controlado de pagos desde Ventas

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare


class EsiSalePaymentWizard(models.TransientModel):
    _name = 'esi.sale.payment.wizard'
    _description = 'Registrar Pago desde Venta'

    sale_order_id = fields.Many2one('sale.order', string='Venta', required=True, readonly=True)
    invoice_choice = fields.Selection(
        selection='_selection_invoices', string='Factura', required=True
    )
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    journal_choice = fields.Selection(
        selection='_selection_payment_journals', string='Forma de Pago', required=True
    )
    amount_due = fields.Monetary(string='Saldo Pendiente', currency_field='currency_id', readonly=True)
    amount = fields.Monetary(string='Importe a Pagar', currency_field='currency_id', required=True)
    payment_date = fields.Date(string='Fecha de Pago', required=True, default=fields.Date.context_today)
    communication = fields.Char(string='Referencia')

    @api.model
    def _get_order_from_context(self):
        order_id = self.env.context.get('default_sale_order_id') or self.env.context.get('sale_order_id')
        if not order_id:
            return self.env['sale.order']
        order = self.env['sale.order'].browse(order_id).exists()
        if order:
            order.check_access_rights('read')
            order.check_access_rule('read')
        return order

    @api.model
    def _selection_invoices(self):
        order = self._get_order_from_context()
        if not order:
            return []
        invoices = order.sudo().invoice_ids.filtered(
            lambda inv: inv.type == 'out_invoice' and inv.state == 'posted' and inv.amount_residual > 0
        ).sorted(key=lambda inv: inv.id, reverse=True)
        return [
            (str(inv.id), '%s - Saldo: %s %s' % (
                inv.name or inv.ref or _('Factura'),
                ('%.2f' % inv.amount_residual),
                inv.currency_id.name or '',
            ))
            for inv in invoices
        ]

    @api.model
    def _allowed_payment_journals(self, order):
        """Diarios Caja/Banco válidos para la compañía y, si existe Store, para la sucursal."""
        if not order:
            return self.env['account.journal']
        Journal = self.env['account.journal'].sudo()
        domain = [
            ('company_id', '=', order.company_id.id),
            ('type', 'in', ('bank', 'cash')),
            ('at_least_one_inbound', '=', True),
        ]
        if 'store_id' in Journal._fields and 'store_id' in order._fields and order.store_id:
            domain += ['|', ('store_id', '=', False), ('store_id', '=', order.store_id.id)]
        return Journal.search(domain, order='type, name, id')

    @api.model
    def _selection_payment_journals(self):
        order = self._get_order_from_context()
        if not order:
            return []
        result = []
        for journal in self._allowed_payment_journals(order):
            payment_type = _('Caja') if journal.type == 'cash' else _('Banco')
            result.append((str(journal.id), '%s - %s' % (payment_type, journal.display_name)))
        return result

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self._get_order_from_context()
        if not order:
            return res
        invoice_choices = self._selection_invoices()
        if not invoice_choices:
            raise UserError(_('No existe una factura publicada con saldo pendiente.'))
        journal_choices = self._selection_payment_journals()
        if not journal_choices:
            raise UserError(_('No existe un diario de Caja o Banco disponible para esta venta.'))

        invoice_id = int(invoice_choices[0][0])
        invoice = self.env['account.move'].sudo().browse(invoice_id)
        res.update({
            'sale_order_id': order.id,
            'invoice_choice': str(invoice.id),
            'partner_id': invoice.partner_id.id,
            'currency_id': invoice.currency_id.id,
            'journal_choice': journal_choices[0][0],
            'amount_due': invoice.amount_residual,
            'amount': invoice.amount_residual,
            'communication': invoice.name or order.name,
        })
        return res

    @api.onchange('invoice_choice')
    def _onchange_invoice_choice(self):
        if not self.invoice_choice or not self.sale_order_id:
            return
        order = self.sale_order_id
        invoice = self.env['account.move'].sudo().browse(int(self.invoice_choice)).exists()
        if invoice and invoice.id in order.sudo().invoice_ids.ids:
            self.partner_id = invoice.partner_id
            self.currency_id = invoice.currency_id
            self.amount_due = invoice.amount_residual
            self.amount = invoice.amount_residual
            self.communication = invoice.name or order.name

    def _get_payment_method(self, journal):
        methods = journal.sudo().inbound_payment_method_ids
        method = methods.filtered(lambda m: m.code == 'manual')[:1] or methods[:1]
        if not method:
            raise UserError(_('No existe un método de cobro configurado para el diario seleccionado.'))
        return method

    def action_register_payment(self):
        self.ensure_one()
        order = self.sale_order_id.exists()
        if not order:
            raise UserError(_('La venta ya no existe.'))
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            raise UserError(_('No tiene acceso a esta venta.'))
        if order.state not in ('sale', 'done'):
            raise UserError(_('La venta debe estar confirmada.'))
        if not self.invoice_choice:
            raise UserError(_('Seleccione una factura.'))
        if not self.journal_choice:
            raise UserError(_('Seleccione una Forma de Pago.'))

        invoice = self.env['account.move'].sudo().browse(int(self.invoice_choice)).exists()
        if not invoice or invoice.id not in order.sudo().invoice_ids.ids:
            raise UserError(_('La factura seleccionada no pertenece a esta venta.'))
        if invoice.type != 'out_invoice' or invoice.state != 'posted':
            raise UserError(_('Solo se puede registrar pago sobre una factura de cliente publicada.'))
        if invoice.company_id != order.company_id:
            raise UserError(_('La factura pertenece a otra compañía.'))
        if invoice.amount_residual <= 0:
            raise UserError(_('La factura ya no tiene saldo pendiente.'))
        if self.amount <= 0:
            raise UserError(_('El importe del pago debe ser mayor que cero.'))
        if float_compare(self.amount, invoice.amount_residual, precision_rounding=invoice.currency_id.rounding) > 0:
            raise UserError(_('El importe no puede ser mayor al saldo pendiente de la factura.'))

        sale_type = order.work_process_order_id
        if not sale_type or not sale_type.allow_payment_from_sale:
            raise UserError(_('El registro de pagos desde Ventas está desactivado para este Tipo de Venta.'))

        try:
            journal_id = int(self.journal_choice)
        except (TypeError, ValueError):
            raise UserError(_('La Forma de Pago seleccionada no es válida.'))
        allowed_journals = self._allowed_payment_journals(order)
        journal = allowed_journals.filtered(lambda j: j.id == journal_id)[:1]
        if not journal:
            raise UserError(_('El diario seleccionado no está disponible para esta venta.'))

        method = self._get_payment_method(journal)
        payment_vals = {
            'partner_id': invoice.partner_id.id,
            'amount': self.amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_method_id': method.id,
            'journal_id': journal.id,
            'payment_date': self.payment_date,
            'communication': self.communication or invoice.name or order.name,
            'currency_id': invoice.currency_id.id,
            'invoice_ids': [(6, 0, [invoice.id])],
            'esi_sale_order_id': order.id,
            'esi_sale_registered_by_id': self.env.user.id,
        }
        payment = self.env['account.payment'].sudo().with_context(
            force_company=order.company_id.id,
            company_id=order.company_id.id,
        ).create(payment_vals)
        payment.post()

        order.message_post(body=_(
            'ESI: %s registró un pago de %s %s mediante %s sobre la factura %s.'
        ) % (
            self.env.user.display_name,
            ('%.2f' % self.amount),
            invoice.currency_id.name,
            journal.display_name,
            invoice.name or '',
        ))
        return {'type': 'ir.actions.act_window_close'}
