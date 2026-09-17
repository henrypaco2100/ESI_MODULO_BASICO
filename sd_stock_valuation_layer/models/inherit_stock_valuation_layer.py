from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_is_zero, float_repr
class SdInheritStockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    # para archivar las valoraciones canceladas
    valuation_detailed = fields.One2many('stock.valuation.detailed', 'stock_valuation_id')
    state = fields.Selection([
        ('confirmed', 'confirmado'),
        ('cancel', 'cancelado')], string='State', default='confirmed')
    #
    # def action_Archivar_valoracion(self):
    #     self.sudo().write({'archivado':True})

    def create_valoracion_detallada(self,vals):
        values = ({
            'stock_valuation_id': self.id,
            'sd_valuation_purchase_id': vals['sd_valuation_purchase_id'],
            'sd_value_detailed': vals['sd_value_detailed'],
            'sd_qty_detailed':vals['sd_qty_detailed'],

        })
        # self.env[self.computer_invoice_line_ids._name].new(values)
        self.env[self.valuation_detailed._name].create(values)
    def action_cancel_valuation_out(self):
        """
        ocupamos los detalles de la valoracion(valuation_detailed)
        para realizar el proceso inverso a la creacion de valoracion de salidas
        """
        for valuation_purchase in self.valuation_detailed:
            remaining_value_new = valuation_purchase.sd_value_detailed + valuation_purchase.sd_valuation_purchase_id.remaining_value
            remaining_qty_new = valuation_purchase.sd_qty_detailed + valuation_purchase.sd_valuation_purchase_id.remaining_qty
            valuation_purchase.sd_valuation_purchase_id.sudo().write({
                'remaining_value': remaining_value_new,
                'remaining_qty': remaining_qty_new,
            })
        self.sudo().write({
            'quantity': 0,
            'unit_cost': 0,
            'value': 0,
            'valuation_detailed': None,
            'state': 'cancel',
        })

    def action_cancel_valuation_in(self):
        """ cancelamos las valoraciones de ingresos colocandolas en 0
                """
        forzar_cancelacion = self.env['res.users'].has_group('sd_stock_valuation_layer.sd_stock_valuation_layer_group_cancelar_purchase')
        if forzar_cancelacion:
            self.sudo().write({
                'quantity': 0,
                'unit_cost': 0,
                'value': 0,
                'remaining_value': 0,
                'remaining_qty': 0,
                'state': 'cancel',
            })
        else:
            self.existen_movimientos_realizados()
            self.sudo().write({
                'quantity': 0,
                'unit_cost': 0,
                'value': 0,
                'remaining_value': 0,
                'remaining_qty': 0,
                'state': 'cancel',
            })
    def existen_movimientos_realizados(self):
        """
        consultar si el
        valor restante igual a valor
        cantidad restante igual a cantidad

        """
        if self.remaining_value != self.value and self.remaining_qty != self.quantity:
            raise UserError(
                _('No es posible continuar!!\nExisten Movientos realizados del producto "%s", consulte a su soporte porfavor!!') % (
                    self.product_id.name))
        return True

    def update_date_valuation(self, date_order):
        parametros = []
        parametros.append(date_order)
        parametros.append(self.id)
        self.env.cr.execute(
            "UPDATE public.stock_valuation_layer SET create_date=%s WHERE id=%s ", (parametros))
    def reprocesar_valoracion_sin_rastreo(self):

        """
        1. esta funcion tendra en cuenta las valoraciones con movimientos cancelados el cual tendra que colocar las valoraciones en 0.
        1.2 tambien se tiene que excluir las valoraciones de coste de destino canceladas.
        2. Esta funcion reprocesara todas las valoraciones de acuerdo a su fecha de creacion.
        3. tambien reprocesara los asientos contables de cada valoracion con relacion a sus movimientos de existencia
        """
        # 1. Realizar valoraciones a 0 con movimientos cancelados

        stock_valuation_layers = self.env['stock.valuation.layer'].search([('state','=','cancel')])
        # 1.2 Realizar valoraciones a 0 de costo de destino cancelados
        # stock_valuation_layers.update(self.env['stock.valuation.layer'].search([('stock_landed_cost_id.state','=','cancel')]))
        for stock_valuation_layer in stock_valuation_layers:
            stock_valuation_layer.sudo().write({
                'quantity': 0,
                'unit_cost': 0,
                'value': 0,
                'remaining_value': 0,
                'remaining_qty': 0,
                'state': 'cancel',
            })
            stock_valuation_layer.sudo().unlink()

        # 2.stock valuation layer Por orden de fecha

        stock_valuation_layers = self.env['stock.valuation.layer'].search([],order='create_date ASC')
        array_id_producto = self.obtener_id_productos(stock_valuation_layers)
        stock_valuation_layers = self.agrupar_por_producto(array_id_producto, stock_valuation_layers)
        for stock_valuation_layer_group in stock_valuation_layers:
            for stock_valuation_layer in stock_valuation_layer_group:
                print("nombre", stock_valuation_layer.product_id.name)
                print("valoracion", stock_valuation_layer.create_date)
                self.tipo_valoracion(stock_valuation_layer)
        raise UserError(
            _('No es posible cancelar una orden con Movimientos realizados, consulte a su soporte porfavor!!'))
    def obtener_id_productos(self,objeto_stock_valuation):
        array_id = []
        for valuation in objeto_stock_valuation:
            if array_id:
                if not valuation.product_id.id in array_id:
                    array_id.append(valuation.product_id.id)
            else:
                array_id.append(valuation.product_id.id)
        return array_id

    # agrupar por productos
    def agrupar_por_producto(self, array_id,objeto_stock_moves):
        nuevo_stock_move=[]
        for id_producto in array_id:
            nuevo_stock_move_por_produto = []
            for stock_move in objeto_stock_moves:
                if stock_move.product_id.id == id_producto:
                    nuevo_stock_move_por_produto.append(stock_move)
            nuevo_stock_move.append(nuevo_stock_move_por_produto)
        return nuevo_stock_move
    def tipo_valoracion(self,valoracion):
        # SALIDA/out
        if valoracion.quantity < 0:
            vals = valoracion.product_id._run_fifo_reprocesar(valoracion.quantity, valoracion.company_id)
            print('cantidad',valoracion.quantity, "valores de ventas",vals,'valor: ', vals['value'])

            # escribir nuevo valor y costo unitario
            valoracion.sudo().write({
                'value': vals['value'],
                'unit_cost': vals['unit_cost'],
            })
            # limpiar anteriores detalles de valoracion
            for detalle_id in valoracion.valuation_detailed:
                detalle_id.unlink()

            # crear nuevo detalle de valoracion
            deatils_valuaiton_ids = vals['details']
            print('detalle',deatils_valuaiton_ids)
            for detail_id in deatils_valuaiton_ids:
                valoracion.create_valoracion_detallada(detail_id)
            # Limpiar anteriores apuntes contables del Asiento contable
            for account_move_id in valoracion.stock_move_id.account_move_ids:
                for line_id in account_move_id.line_ids:
                    line_id.sudo().unlink()
            # modificar asientos contables Out
            valoracion.stock_move_id._account_entry_move(valoracion.quantity, valoracion.description, valoracion.id, valoracion.value)
            # for account_move_id in valoracion.stock_move_id.account_move_ids:
            #     print('Asientos Contables', account_move_id.name)
            #     account_move_id.write_account_move_out_valuation(valoracion)

        # ENTRADA/in
        elif valoracion.quantity > 0:
            valoracion.sudo().write({
                'remaining_value': valoracion.value,
                'remaining_qty': valoracion.quantity,
            })
            # # modificar asientos contables Out
            # for account_move_id in valoracion.stock_move_id.account_move_ids:
            #     account_move_id.write_account_move_out_valuation(valoracion)

        # coste de destino
        elif valoracion.quantity == 0 and valoracion.value > 0:
            for stock_valuation_layer_id in valoracion.stock_move_id.stock_valuation_layer_ids:
                if not stock_valuation_layer_id.stock_landed_cost_id:
                    # comprobar si la compra tiene movientos para agregarle el coste de destino
                    if not stock_valuation_layer_id.remaining_value == stock_valuation_layer_id.value and stock_valuation_layer_id.remaining_qty == stock_valuation_layer_id.quantity:
                        if stock_valuation_layer_id.create_date > valoracion.create_date:
                            raise UserError(
                                _('No es posible continuar con el reprocesar,\nla fecha del coste de destino "%s" es mayor a la fecha de su compra!!') % (
                                    valoracion.stock_landed_cost_id.name))

                        raise UserError(
                            _('No es posible continuar con el reprocesar,\nuna entrada tiene movimientos realizados y no se puede agregar el coste de destino "%s"!!') % (valoracion.stock_landed_cost_id.name))
                    # Agregar el coste de destino a la valoracion de entrada (compra)
                    stock_valuation_layer_id.sudo().write({'remaining_value': stock_valuation_layer_id.remaining_value+ valoracion.value})
                    break

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.company.sd_date_ini_management:
            domain.append(['create_date', '>=', self.env.company.sd_date_ini_management])
        return super(SdInheritStockValuationLayer, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.company.sd_date_ini_management:
            domain.append(['create_date', '>=', self.env.company.sd_date_ini_management])
        res = super(SdInheritStockValuationLayer, self).read_group(domain, fields, groupby, offset=offset,limit=limit, orderby=orderby,lazy=lazy)
        return res