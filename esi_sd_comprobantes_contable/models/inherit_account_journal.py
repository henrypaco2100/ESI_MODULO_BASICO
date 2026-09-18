from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SdInheritAccountJournalMejoras(models.Model):
    _inherit = "account.journal"

    sd_show_glosa = fields.Boolean('Mostrar Glosa')
