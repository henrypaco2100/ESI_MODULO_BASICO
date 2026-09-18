from odoo import models, fields

class CustomConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sd_filter_uom = fields.Boolean(config_parameter='stock.sd_filter_uom', string="Filtrar Unidades de Medida")
    sd_reportes_transf_interna = fields.Boolean(config_parameter='stock.sd_reportes_transf_interna', string="Reportes Transferencia Interna")

