from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet

class SdInheritStockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    sd_precio_product = fields.Float(string='Precio Unitario',default=0.0)

class SdInheritStockInventoryPrecioProducto(models.Model):
    _inherit = 'stock.inventory'
    def action_validate(self):
        """
        herencia para escribir
        """
        for line_id in self.line_ids:
            if line_id.sd_precio_product != 0:
                line_id.product_id.sudo().write({
                    'standard_price': line_id.sd_precio_product
                })
        res = super(SdInheritStockInventoryPrecioProducto,self).action_validate()
        return res