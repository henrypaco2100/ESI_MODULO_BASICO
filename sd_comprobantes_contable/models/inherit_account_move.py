from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SdInheritAccountMoveMejoras(models.Model):
    _inherit = "account.move"

    # Campo original del modulo: controla si el comprobante imprime FECHA
    # en cada linea contable.
    sd_is_fecha = fields.Boolean('Columna Fecha')

    # ESI correccion 2026-09-01:
    # Opciones del comprobante. No se guardan en account.move.line porque
    # solamente controlan la presentacion del reporte del asiento.
    sd_show_cash_flow = fields.Boolean('Mostrar CTA Flujo')
    sd_show_analytic = fields.Boolean('Mostrar Analítica')
