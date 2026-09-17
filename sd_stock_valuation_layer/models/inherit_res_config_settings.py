from odoo import models, fields


class SdCustomConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sd_is_change_price_valuation = fields.Boolean(default=False , string='Generar Valoracion en AVCO(Promedio) al cambiar el Coste del producto',config_parameter='stock.sd_is_change_price_valuation')
    sd_is_change_cost_method_and_val = fields.Boolean(default=False , string='Generar Valoracion al cambiar Método de coste y Valoración del inventario',config_parameter='stock.sd_is_change_cost_method_and_val')
