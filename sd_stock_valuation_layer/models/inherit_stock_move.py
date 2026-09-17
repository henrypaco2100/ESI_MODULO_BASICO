
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet

class SdInheritStockMove(models.Model):
    _inherit = "stock.move"

    def _create_out_svl(self, forced_quantity=None):
        """ metodo sobrescrito de stock.move del modulo stock_account
        para realizar el detalle de valoracion
        """
        svl_vals_list = []
        details_valuation = []
        for move in self:
            move = move.with_context(force_company=move.company_id.id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            if move.product_id.tracking in ('lot','serial'):
                move_line_ids = move.move_line_ids.filtered(lambda line: line.qty_done != 0)
                svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id,move_line_ids=move_line_ids)
            else:
                svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')

            # detalle de la valoracion -Henry
            # details_valuation.append(svl_vals.pop('details'))
            svl_vals_list.append(svl_vals)
        object_valuationes = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        # crear detalle de la valoracion
        # i = 0
        # while i < len(object_valuationes):
        #     for vals in details_valuation[i]:
        #         object_valuationes[i].create_valoracion_detallada(vals)
        #     i = i + 1
        return object_valuationes

    def reprocesar_movimiento_existencias(self,fecha_inicio=None):
        # print("reprocesar")
        """Se Reprocesara todos los Movimientos de existencias , MOvimientos de producto,
         stock de la ubicaciones(stock.quant) o informe de inventario y las valorarion de inventario con sus asientos contables"""

        # Algunas Observaciones
        """
        MULTIPLES MOVIMIENTOS DE PRODUCTOS
        1.      si es lote por serie unica  se da el caso de muchos movimientos de producto en un movimiento de existencia
        1.2     lo mismo pasa con la valoraciones en este caso
        
        MULTIPLES VALORACIONES
        2.      si existe coste de destino puede generarse muchas valoraciones relacionado a un movimiento de existencia
        
        MULTIPLES ASIENTOS CONTABLES 
        3.      
        """
        if not self.env['res.users'].has_group('sd_stock_valuation_layer.sd_grupo_permiso_reprocesar_movimientos_existencia'):
            raise UserError(_('Usted no tiene permiso para realizar esta acción\nPorfavor consulte con su tecnico'))
        #Comenzar Logica Gestion
        if fecha_inicio:
            stock_move_ids = self.env['stock.move'].sudo().search([('state','=','done'),('product_id.type','=','product' ),('date','>=',fecha_inicio)],order='date ASC')
        else:
            stock_move_ids = self.env['stock.move'].sudo().search([('state', '=', 'done'), ('product_id.type', '=', 'product')],order='date ASC')

        stock_move_agrupados = []    # array para agrupar por producto
        for stock_move_id in stock_move_ids:
            if stock_move_agrupados:
                si_existe = False
                for stock_move_agrupado in stock_move_agrupados:
                    if stock_move_id.product_id == stock_move_agrupado['product_id']:
                        stock_move_agrupado['stock_move_ids'].append(stock_move_id)
                        si_existe = True
                if not si_existe:
                    vals = {
                        'product_id': stock_move_id.product_id,
                        'stock_move_ids': [stock_move_id],
                    }
                    stock_move_agrupados.append(vals)
            else:
                vals = {
                    'product_id': stock_move_id.product_id,
                    'stock_move_ids': [stock_move_id],
                }
                stock_move_agrupados.append(vals)

        # Eliminar todos los stock_quant
        aux = self.env['stock.quant'].sudo().search([]).unlink()

        #ELiminar las valoraciones que no tienen movimiento de existencia
        for valoracion in self.env['stock.valuation.layer'].search([('stock_move_id','=',False)]):
            valoracion.sudo().unlink()
        # ELiminar las valoraciones que no tienen movimiento estan cancelados o en otro estado que no se hecho
        for valoracion in self.env['stock.valuation.layer'].search([('stock_move_id.state', '!=', 'done')]):
            valoracion.sudo().unlink()

        for stock_move_agrupado in stock_move_agrupados:
            # Clasificar por Tipo de Movimiento segun sus ubicaciones
            for stock_move in stock_move_agrupado['stock_move_ids']:
                # print('Movimiento name',stock_move.reference,stock_move.product_id.name,'cant',stock_move.product_uom_qty)
                # print('tipo',stock_move.picking_id.name, stock_move.picking_id.sale_id.name,stock_move.picking_id.purchase_id.name,stock_move.inventory_id.name,stock_move.production_id.name)
                # reprocesar por tipo de operaciones
                if stock_move.picking_type_id:

                    # ENTRADAS
                    if stock_move.picking_type_id.code =='incoming':
                        stock_move.reprocesar_movimientos_in()

                    #SALIDAS
                    elif stock_move.picking_type_id.code == 'outgoing':
                        stock_move.reprocesar_movimientos_out()

                    #PRODUCCION
                    if stock_move.picking_type_id.code == 'mrp_operation':
                        #Producto Final Entrada
                        if stock_move.location_id.usage == 'production' and stock_move.location_dest_id.usage == 'internal':
                            stock_move.reprocesar_movimientos_in()
                        #Materia Prima salida
                        if stock_move.location_id.usage == 'internal' and stock_move.location_dest_id.usage == 'production':
                            if stock_move.production_id:
                                stock_move.reprocesar_movimientos_out(is_produccion=True)
                            else:
                                stock_move.reprocesar_movimientos_out(is_produccion=True)
                # AJUSTE DE INVENTARIO
                elif stock_move.inventory_id:

                    # Ajuste de Inventario SALIDAS
                    if stock_move.location_id.usage == 'internal' and stock_move.location_dest_id.usage == 'inventory':
                        stock_move.reprocesar_movimientos_out(is_inventory=True)

                    # AJUSTE DE INVENTARIO ENTRADAS
                    if stock_move.location_id.usage == 'inventory' and stock_move.location_dest_id.usage == 'internal':
                        stock_move.reprocesar_movimientos_in()

        return True
    def reprocesar_movimientos_in(self):
        # Movimientos de Productos
        # INFORME DE INVENTARIO IN
        for move_line in self.move_line_ids.filtered(lambda line: line.state == 'done'):
            lote_serie = None
            if self.product_id.tracking in ('lot', 'serial'):
                lote_serie = ('lot_id', '=', move_line.lot_id.id)
            stock_quant_origen = self._return_stock_quant_origen(lote_serie)
            stock_quant_destino = self._return_stock_quant_destino(lote_serie)

            # Ubicacion Origen
            if stock_quant_origen:
                # cantidad_anterior = stock_quant_origen.quantity
                stock_quant_origen.quantity = stock_quant_origen.quantity - move_line.qty_done
            else:
                vals = {'product_id': self.product_id.id,
                        'location_id': self.location_id.id,
                        'in_date': self.date,
                        'lot_id': move_line.lot_id.id if move_line.lot_id else None,
                        'quantity': -move_line.qty_done,
                        }
                self.env['stock.quant'].sudo().create(vals)

            # Ubicacion Destino
            if stock_quant_destino:
                stock_quant_destino.quantity = stock_quant_destino.quantity + move_line.qty_done
            else:
                vals = {'product_id': self.product_id.id,
                        'location_id': self.location_dest_id.id,
                        'in_date': self.date,
                        'lot_id': move_line.lot_id.id if move_line.lot_id else None,
                        'quantity': move_line.qty_done,
                        }
                self.env['stock.quant'].sudo().create(vals)

        # VALORACIONES IN
        valoracion_in_normal = []
        for stock_valuation_layer_id in self.stock_valuation_layer_ids:
            if stock_valuation_layer_id.stock_landed_cost_id if hasattr(stock_valuation_layer_id,
                                                                        'stock_landed_cost_id') else None:
                # Es coste de destino
                if valoracion_in_normal:
                    for valoracion in valoracion_in_normal:
                        if valoracion.remaining_qty == valoracion.quantity:
                            if valoracion.create_date > stock_valuation_layer_id.create_date:
                                raise UserError(
                                    _('No es posible continuar con el reprocesar,\nla fecha del coste de destino "%s" es menor a la fecha de su compra!!') % (
                                        stock_valuation_layer_id.stock_landed_cost_id.name))
                            else:
                                # Agregar el coste de destino a la valoracion de entrada (compra)
                                valoracion.sudo().write(
                                    {'remaining_value': valoracion.remaining_value + stock_valuation_layer_id.value})
                        else:
                            raise UserError(
                                _('No es posible continuar con el reprocesar,\nuna entrada tiene movimientos realizados y no se puede agregar el coste de destino "%s"!!') % (
                                    valoracion.stock_landed_cost_id.name))
                else:
                    raise UserError(
                        _('No es posible continuar con el reprocesar,\nla fecha del coste de destino "%s" es menor a la fecha de su compra!!\nRevise la compra y el coste de Destino.\nEl coste de destino puede no estar relacionado con una Entrada(Compra)') % (
                            stock_valuation_layer_id.stock_landed_cost_id.name))

            else:
                # Entrada normal
                stock_valuation_layer_id.sudo().write({
                    'remaining_value': stock_valuation_layer_id.value,
                    'remaining_qty': stock_valuation_layer_id.quantity,
                })
                valoracion_in_normal.append(stock_valuation_layer_id)
    def reprocesar_movimientos_out(self,is_produccion=None,is_inventory=None):
        # Movimientos de Productos
        # INFORME DE INVENTARIO OUT
        for move_line in self.move_line_ids.filtered(lambda line: line.state == 'done'):
            lote_serie = None
            lote_mensaje = ''
            if self.product_id.tracking in ('lot', 'serial'):
                lote_serie = ('lot_id', '=', move_line.lot_id.id)
                lote_mensaje = 'del Lote ' + move_line.lot_id.name
            stock_quant_origen = self._return_stock_quant_origen( lote_serie)
            stock_quant_destino = self._return_stock_quant_destino( lote_serie)

            # Ubicacion Origen
            if stock_quant_origen and stock_quant_origen.quantity >= move_line.qty_done:
                stock_quant_origen.quantity = stock_quant_origen.quantity - move_line.qty_done
            else:
                if is_produccion:
                    raise UserError(
                        _('No es posible continuar con el reprocesar!!\nSe esta Reprocesando una Produccion("%s") con el producto materia prima("%s") ' + lote_mensaje + ' sin stock disponible revise los siguientes puntos:'
                             '\n  - No se Realizo una entrada(Compra, Ajuste de Inventario de entrada)'
                             '\n  - La fecha de la Entrada(Compra,Ajuste Inventario) es Mayor a la Venta') % (
                            self.production_id.name or self.reference,
                            self.product_id.name))
                elif is_inventory:
                    raise UserError(
                        _('No es posible continuar con el reprocesar!!\nSe esta Reprocesando una Ajuste Inicial de Salida("%s") con el producto("%s") ' + lote_mensaje + ' sin stock disponible revise los siguientes puntos:'
                             '\n  - No se Realizo una entrada(Compra, Ajuste de Inventario de entrada)'
                             '\n  - La fecha de la Entrada(Compra,Ajuste Inventario) es Mayor a la del Ajuste Inicial') % (
                            self.inventory_id.name or self.name,
                            self.product_id.name))
                else:
                    raise UserError(
                        _('No es posible continuar con el reprocesar!!\nSe esta Reprocesando una Venta o pedido de POS("%s") con el producto("%s") ' + lote_mensaje + ' sin stock disponible revise los siguientes puntos:'
                          '\n  - No se Realizo una entrada(Compra, Ajuste de Inventario de entrada)'
                          '\n  - La fecha de la Entrada(Compra,Ajuste Inventario) es Mayor a la Venta') % (
                            self.sale_line_id.order_id.name or self.picking_id.sale_id.name or self.picking_id.origin,
                            self.product_id.name or self.sale_line_id.product_id.name))

            # Ubicacion Destino
            if stock_quant_destino:
                stock_quant_destino.quantity = stock_quant_destino.quantity + move_line.qty_done
            else:
                vals = {'product_id': self.product_id.id,
                        'location_id': self.location_dest_id.id,
                        'in_date': self.date,
                        'lot_id': move_line.lot_id.id if move_line.lot_id else None,
                        'quantity': move_line.qty_done,
                        }
                self.env['stock.quant'].sudo().create(vals)

        # VALORACIONES OUT
        asientos_contables = self.env['account.move'].search([('type', '=', 'entry'),
                                                              ('stock_move_id', '=', self.id),
                                                              ('stock_valuation_layer_ids', 'in',
                                                               self.stock_valuation_layer_ids.filtered(
                                                                   lambda line: line.quantity != 0).ids),
                                                              ('state', '=', 'posted')])

        # Asiento de Revaloracion o regularizados CANCELAR
        asientos_contables_regularizados = self.env['account.move'].search([('type', '=', 'entry'),
                                                                            ('stock_move_id', '=', self.id),
                                                                            ('stock_valuation_layer_ids', 'in',
                                                                             self.stock_valuation_layer_ids.filtered(
                                                                                 lambda line: line.quantity == 0).ids),
                                                                            ('state', '=', 'posted')])
        for asiento_contable_regularizado in asientos_contables_regularizados:
            asiento_contable_regularizado.button_draft()
            asiento_contable_regularizado.button_cancel()
            asiento_contable_regularizado.update({'stock_move_id': None, })
        # Limpiar anteriores valoraciones
        for stock_valuation_layer_id in self.stock_valuation_layer_ids:
            for valuation_detailed in stock_valuation_layer_id.valuation_detailed:
                valuation_detailed.sudo().unlink()
            stock_valuation_layer_id.sudo().unlink()
        # Crear nueva Valoracion
        new_stock_valuation = self._update_out_svl(is_sale=True)
        # Crear o Actualizar Asientos Contables
        if not new_stock_valuation.product_id.valuation == 'real_time':
            raise UserError(
                _('No es posible continuar con el reprocesar,\nLa Valoración del Inventario del producto %s no es: Automatizado\nSi desea continuar configure el producto o su categoria!!') % (
                    new_stock_valuation.product_id.name))
        if asientos_contables:
            for accocun_move_id in asientos_contables:
                accocun_move_id.button_draft()
                accocun_move_id.line_ids.sudo().unlink()
                self._update_account_entry_move(new_stock_valuation.quantity, new_stock_valuation.description,
                                                      new_stock_valuation.id, new_stock_valuation.value,
                                                      accocun_move_id)
        else:
            self._account_entry_move(new_stock_valuation.quantity, new_stock_valuation.description,
                                           new_stock_valuation.id, new_stock_valuation.value)
    def _update_out_svl(self, is_sale=None):
        """ Este metódo actualiza las valoraciones y sus detalles para el Reprocesar"""

        details_valuation = []
        move = self.with_context(force_company=self.company_id.id)
        valued_move_lines = move._get_out_move_lines()
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                 move.product_id.uom_id)
        if move.product_id.tracking in ('lot','serial'):
            move_line_ids = move.move_line_ids.filtered(lambda line: line.qty_done != 0)
            svl_vals = move.product_id._prepare_out_svl_vals(valued_quantity, move.company_id,move_line_ids=move_line_ids)
        else:
            svl_vals = move.product_id._prepare_out_svl_vals(valued_quantity, move.company_id)
        svl_vals.update(move._prepare_common_svl_vals())
        svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')

        # Actualizar Detalle de la valoracion -Henry
        # details_valuation = svl_vals.pop('details')
        object_valuation = self.env['stock.valuation.layer'].sudo().create(svl_vals)
        object_valuation.update_date_valuation(move.date or move.sale_line_id.order_id.date_order if is_sale else fields.Datetime.now())
        # crear detalle de la valoracion
        # for vals in details_valuation:
        #     object_valuation.create_valoracion_detallada(vals)
        return object_valuation

    def _update_account_entry_move(self,qty, description, svl_id, cost,account_move_id):
        """ Actualizar asientos contables de la Anterior Valoracion
            Para eso le pasamos el objeto asiento contable a actualizar : account_move_id
        """
        self.ensure_one()
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return False
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return False

        location_from = self.location_id
        location_to = self.location_dest_id
        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._update_account_move_line_reprocesar(acc_dest, acc_valuation,
                                                                                         journal_id, qty, description,
                                                                                         svl_id, cost,account_move_id)
            else:
                self.with_context(force_company=company_to.id)._update_account_move_line_reprocesar(acc_src, acc_valuation,
                                                                                         journal_id, qty, description,
                                                                                         svl_id, cost,account_move_id)

        # Create Journal Entry for products leaving the company
        if self._is_out():
            cost = -1 * cost
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._update_account_move_line_reprocesar(acc_valuation, acc_src,
                                                                                           journal_id, qty, description,
                                                                                           svl_id, cost,account_move_id)
            else:
                self.with_context(force_company=company_from.id)._update_account_move_line_reprocesar(acc_valuation, acc_dest,
                                                                                           journal_id, qty, description,
                                                                                           svl_id, cost,account_move_id)

        return True

    def _update_account_move_line_reprocesar(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost,account_move_id):
        """Actualizar Apuntes Contables"""
        self.ensure_one()
        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            # date = self._context.get('force_period_date', fields.Date.context_today(self))
            account_move_id.sudo().update({
                # 'journal_id': journal_id,
                'line_ids': move_lines,
                # 'date': date,
                'ref': description,
                'stock_move_id': self.id,
                'stock_valuation_layer_ids': [(6, None, [svl_id])],
                # 'type': 'entry',
            })
            account_move_id.action_post()

    def _return_stock_quant_origen(self, lote_serie=None):
        if lote_serie:
            return self.env['stock.quant'].search([
                ('location_id', '=', self.location_id.id),
                ('product_id', '=', self.product_id.id), lote_serie])
        else:
            return self.env['stock.quant'].search([
                ('location_id', '=', self.location_id.id),
                ('product_id', '=', self.product_id.id)])

    def _return_stock_quant_destino(self,lote_serie=None):
        if lote_serie:
            return self.env['stock.quant'].search([
                                ('location_id','=',self.location_dest_id.id),
                                ('product_id','=',self.product_id.id),lote_serie])
        else:
            return self.env['stock.quant'].search([
                ('location_id', '=', self.location_dest_id.id),
                ('product_id', '=', self.product_id.id)])

    def _update_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        move = self.with_context(force_company=self.company_id.id)
        valued_move_lines = move._get_in_move_lines()
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                 move.product_id.uom_id)
        unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
        if move.product_id.cost_method == 'standard':
            unit_cost = move.product_id.standard_price
        svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
        svl_vals.update(move._prepare_common_svl_vals())
        if forced_quantity:
            svl_vals[
                'description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
        return self.env['stock.valuation.layer'].sudo().create(svl_vals)