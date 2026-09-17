from odoo import models, fields, api, _

class InheritAccountGroup(models.Model):
    _inherit = 'account.analytic.account'

    sd_codigo = fields.Char('Codigo', required="True")

    def name_get(self):
        result = []
        for partner in self:
            # print('sdcodigo: ', partner.sd_codigo, partner.name)
            if partner.sd_codigo:
                name = partner.sd_codigo + ' ' + partner.name
            else:
                name = partner.name
            result.append((partner.id, name))
        return result
