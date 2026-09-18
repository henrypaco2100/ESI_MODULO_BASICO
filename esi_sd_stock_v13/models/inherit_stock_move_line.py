from odoo import api, fields, models,SUPERUSER_ID,_

class InheritStockMoveLineMejora(models.Model):
    _inherit = "stock.move.line"

    @api.depends('product_id','location_id','product_uom_qty','qty_done')
    def compute_stock_disponible_ubicacion(self):
        for stock_move_line in self:
            stock_disponible = 0
            stock_quants = self.env['stock.quant'].search([('location_id', '=', stock_move_line.location_id.id),
                                                           ('product_id', '=', stock_move_line.product_id.id),
                                                           ('location_id.usage', '=', 'internal')])

            if stock_move_line.lot_id:
                stock_quants = self.env['stock.quant'].search([('location_id', '=', stock_move_line.location_id.id),
                                                               ('product_id', '=', stock_move_line.product_id.id),
                                                               ('location_id.usage', '=', 'internal'),
                                                               ('lot_id', '=', stock_move_line.lot_id.id)])
            for stock_quant in stock_quants:
                stock_disponible += stock_quant.quantity
            stock_move_line.update({
                'sd_stock_disponible':stock_disponible
            })
    sd_stock_disponible = fields.Float('Stock Disponible',compute='compute_stock_disponible_ubicacion',store=False)