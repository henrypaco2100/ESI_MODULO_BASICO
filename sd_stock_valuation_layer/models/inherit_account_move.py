from odoo import fields, models, tools,_
from odoo.exceptions import AccessError, UserError
class SdInheritAccountMove(models.Model):
    _inherit = 'account.move'
    
    def write_account_move_in_valuation(self):
        print('hello in')
    def write_account_move_out_valuation(self,valoracion):
        if len(self.line_ids):
            cuenta_salidad = self.line_ids.filtered(
                lambda x: x.account_id == valoracion.product_id.categ_id.property_stock_account_output_categ_id)
            print('cuenta salida',cuenta_salidad,valoracion.quantity,valoracion.value, valoracion.value)
            cuenta_salidad.sudo().write({
                'quantity': valoracion.quantity,
                'debit': valoracion.value,
                'balance': valoracion.value
            })
            cuenta_valoracion_por_stock = self.line_ids.filtered(
                lambda x: x.account_id == valoracion.product_id.categ_id.property_stock_valuation_account_id)
            print('cuenta por stock',cuenta_valoracion_por_stock,valoracion.quantity,valoracion.value, -valoracion.value)
            cuenta_valoracion_por_stock.sudo().write({
                'quantity': valoracion.quantity,
                'credit': valoracion.value,
                'balance': -valoracion.value
            })
        else:
            raise UserError(
                _('EL producto "%s" del movimiento de existencia "%s" tiene mas de 1 asiento contable.\nNo es posible continuar, consulte a su soporte porfavor!!')%(valoracion.product_id.name,valoracion.stock_move_id.name))