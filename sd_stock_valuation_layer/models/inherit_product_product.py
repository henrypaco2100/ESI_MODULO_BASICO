from odoo import fields,api, models, tools,_
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr, float_compare

class SdInheritProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'force_company')
    def _compute_value_svl(self):
        """Compute `value_svl` and `quantity_svl`."""
        company_id = self.env.context.get('force_company', self.env.company.id)
        domain = [
            ('product_id', 'in', self.ids),
            ('company_id', '=', company_id),
        ]
        if self.env.context.get('to_date') or self.env.company.sd_date_end_management:
            to_date = fields.Datetime.to_datetime(self.env.context.get('to_date') or self.env.company.sd_date_end_management)
            domain.append(('create_date', '<=', to_date))
        if self.env.company.sd_date_ini_management:
            ini_date = fields.Datetime.to_datetime(self.env.company.sd_date_ini_management)
            domain.append(('create_date', '>=', ini_date))
        groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'])
        products = self.browse()
        for group in groups:
            product = self.browse(group['product_id'][0])
            product.value_svl = self.env.company.currency_id.round(group['value'])
            product.quantity_svl = group['quantity']
            products |= product
        remaining = (self - products)
        remaining.value_svl = 0
        remaining.quantity_svl = 0
    def _prepare_out_svl_vals(self, quantity, company,move_line_ids = None):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': quantity * self.standard_price,
            'unit_cost': self.standard_price,
            'quantity': quantity,
        }

        if self.cost_method in ('average', 'fifo'):
            # Agregar lote y serie unicas-HENRY
            if move_line_ids:
                fifo_vals = {
                    'value': 0,
                    'unit_cost': 0,
                    'valuation_detailed': None,
                    'remaining_qty':0
                }
                for move_line_id in move_line_ids:
                    vals_2 = self._run_fifo(abs(move_line_id.qty_done), company, lote_serie_id=move_line_id.lot_id)
                    fifo_vals['value'] = fifo_vals['value'] + vals_2['value']
                    fifo_vals['remaining_qty'] = fifo_vals['remaining_qty'] + (vals_2.get('remaining_qty') or 0)
                    fifo_vals['valuation_detailed'] = vals_2['valuation_detailed']
                fifo_vals['unit_cost'] = abs(fifo_vals['value'])/abs(quantity)
            else:
                fifo_vals = self._run_fifo(abs(quantity), company)
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')
            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.cost_method == 'average':
                vals['valuation_detailed'] = fifo_vals['valuation_detailed']

                currency = self.env.company.currency_id
                rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
                if rounding_error:
                    # If it is bigger than the (smallest number of the currency * quantity) / 2,
                    # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                    if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                        vals['value'] += rounding_error
                        vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                            '+' if rounding_error > 0 else '',
                            float_repr(rounding_error, precision_digits=currency.decimal_places),
                            currency.symbol
                        )
            if self.cost_method == 'fifo':
                vals.update(fifo_vals)
        if self.cost_method == 'standard':
            vals.update({'valuation_detailed': None})
        return vals
    def _run_fifo(self, quantity, company, lote_serie_id=None):
        self.ensure_one()
        # redondear -Henry
        quantity = round(quantity, 6)
        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        # Agregar lote y serie unicas-HENRY
        if lote_serie_id:
            candidates = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
                ('stock_move_id.move_line_ids.lot_id','in',[lote_serie_id.id]),
                ('stock_move_id.state','=','done'),
                ('product_id', '=', self.id),
                ('remaining_qty', '>', 0),
                ('company_id', '=', company.id),
            ], order='create_date ASC')
        else:
            candidates = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
                ('product_id', '=', self.id),
                ('remaining_qty', '>', 0),
                ('company_id', '=', company.id),
            ], order='create_date ASC')
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        # lista del detalle -Henry
        detailed_valuation = []
        for candidate in candidates:
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }

            candidate.write(candidate_vals)

            # realizar la obtencion de datos de la valoracion de salida
            detailed = {
                'sd_valuation_purchase_id': candidate.id,
                'sd_value_detailed': value_taken_on_candidate,
                'sd_qty_detailed': qty_taken_on_candidate,
            }
            detailed_valuation.append(detailed)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_context(force_company=company.id).standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }

        vals.update({'valuation_detailed': [(0, 0, line_vals) for line_vals in detailed_valuation]})
        return vals

     ##NO GENERAR VALORACION AL CAMBIAR DE COSTE DE DESTINO CUANDO ES AVCO
    def _change_standard_price(self, new_price, counterpart_account_id=False):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.
        svl_vals_list = []
        company_id = self.env.company
        for product in self:
            is_change_price_valuation = self.env['ir.config_parameter'].sudo().get_param('stock.sd_is_change_price_valuation')
            if is_change_price_valuation:
                if product.cost_method not in ('standard','average'):
                    continue
            else:
                if product.cost_method not in ('standard'):
                    continue
            quantity_svl = product.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            diff = new_price - product.standard_price
            value = company_id.currency_id.round(quantity_svl * diff)
            if company_id.currency_id.is_zero(value):
                continue

            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
                'description': _('Product value manually modified (from %s to %s)') % (product.standard_price, new_price),
                'value': value,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

        # Handle account moves.
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        am_vals_list = []
        for stock_valuation_layer in stock_valuation_layers:
            product = stock_valuation_layer.product_id
            value = stock_valuation_layer.value

            if product.type != 'product' or product.valuation != 'real_time':
                continue

            # Sanity check.
            if counterpart_account_id is False:
                raise UserError(_('You must set a counterpart account.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

            if value < 0:
                debit_account_id = counterpart_account_id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = counterpart_account_id

            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                'line_ids': [(0, 0, {
                    'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'product_id': product.id,
                })],
            }
            am_vals_list.append(move_vals)
        account_moves = self.env['account.move'].create(am_vals_list)
        if account_moves:
            account_moves.post()

        # Actually update the standard price.
        self.with_context(force_company=company_id.id).sudo().write({'standard_price': new_price})

class ProductCategory(models.Model):
    _inherit = 'product.category'

    def write(self, vals):
        impacted_categories = {}
        move_vals_list = []
        Product = self.env['product.product']
        SVL = self.env['stock.valuation.layer']
        is_change_cost_method_and_val = self.env['ir.config_parameter'].sudo().get_param('stock.sd_is_change_cost_method_and_val')
        if is_change_cost_method_and_val:
            if 'property_cost_method' in vals or 'property_valuation' in vals:
                # When the cost method or the valuation are changed on a product category, we empty
                # out and replenish the stock for each impacted products.
                new_cost_method = vals.get('property_cost_method')
                new_valuation = vals.get('property_valuation')

                for product_category in self:
                    valuation_impacted = False
                    if new_cost_method and new_cost_method != product_category.property_cost_method:
                        valuation_impacted = True
                    if new_valuation and new_valuation != product_category.property_valuation:
                        valuation_impacted = True
                    if valuation_impacted is False:
                        continue

                    # Empty out the stock with the current cost method.
                    if new_cost_method:
                        description = _("Costing method change for product category %s: from %s to %s.") \
                                      % (
                                      product_category.display_name, product_category.property_cost_method, new_cost_method)
                    else:
                        description = _("Valuation method change for product category %s: from %s to %s.") \
                                      % (product_category.display_name, product_category.property_valuation, new_valuation)
                    out_svl_vals_list, products_orig_quantity_svl, products = Product \
                        ._svl_empty_stock(description, product_category=product_category)
                    out_stock_valuation_layers = SVL.sudo().create(out_svl_vals_list)
                    if product_category.property_valuation == 'real_time':
                        move_vals_list += Product._svl_empty_stock_am(out_stock_valuation_layers)
                    impacted_categories[product_category] = (products, description, products_orig_quantity_svl)

            res = super(ProductCategory, self).write(vals)

            for product_category, (products, description, products_orig_quantity_svl) in impacted_categories.items():
                # Replenish the stock with the new cost method.
                in_svl_vals_list = products._svl_replenish_stock(description, products_orig_quantity_svl)
                in_stock_valuation_layers = SVL.sudo().create(in_svl_vals_list)
                if product_category.property_valuation == 'real_time':
                    move_vals_list += Product._svl_replenish_stock_am(in_stock_valuation_layers)

            # Create the account moves.
            if move_vals_list:
                account_moves = self.env['account.move'].create(move_vals_list)
                account_moves.post()
            return res
        res = super(ProductCategory, self).write(vals)
        return res