from odoo import models, fields, api, _
from odoo.exceptions import UserError
class SdPdfViewer(models.Model):
    _name = 'pdf.viewer'

    name = fields.Char('Nombre')
    sd_archivo = fields.Binary('Adjunto')