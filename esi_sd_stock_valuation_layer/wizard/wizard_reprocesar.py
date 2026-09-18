from odoo import api, fields, models, _

class WizardReprocesar(models.TransientModel):
    _name = "wizard.reprocesar"
    _description = "Asistente para realizar el Reprocesar"
    # _inherit = ['stock.move']

    sd_fecha_inicio = fields.Datetime(string='Fecha Inicio')

    def realizar_valoracion_wizard(self):
        self.env['stock.move'].sudo().reprocesar_movimiento_existencias(self.sd_fecha_inicio)