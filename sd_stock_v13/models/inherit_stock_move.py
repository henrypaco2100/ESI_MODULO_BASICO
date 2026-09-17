from odoo import api, fields, models,SUPERUSER_ID,_

class InheritStockMoveMejora(models.Model):
    _inherit = "stock.move"
    # stock_valuation_layer_ids = fields.Char('eliminar este campo')

    @api.depends('product_id','location_id','product_uom_qty')
    def compute_stock_disponible_ubicacion(self):
        for stock_move in self:
            stock_disponible = 0
            stock_quants = self.env['stock.quant'].search([('location_id','=',stock_move.location_id.id),('product_id','=',stock_move.product_id.id),('location_id.usage','=','internal')])
            for stock_quant in stock_quants:
                stock_disponible += stock_quant.quantity
            stock_move.update({
                'sd_stock_disponible':stock_disponible
            })
    sd_stock_disponible = fields.Float('Stock Disponible',compute='compute_stock_disponible_ubicacion',store=False)
    sd_valuation = fields.Float(compute='_sd_compute_valuation_layer',string='Valoracion',store=True,digits='Product Price')
    sd_valuation_abs = fields.Float(string="Valoracion abs", compute='_compute_sd_valuation_abs',digits='Product Price')

    @api.depends('stock_valuation_layer_ids')
    def _sd_compute_valuation_layer(self):
        for record in self:
            value_total = 0
            for valuation_layer in record.stock_valuation_layer_ids:
                value_total += valuation_layer.value
            record.write({
                'sd_valuation': value_total,
            })

    @api.depends('sd_valuation')
    def _compute_sd_valuation_abs(self):
        for record in self:
            record.sd_valuation_abs = abs(record.sd_valuation)