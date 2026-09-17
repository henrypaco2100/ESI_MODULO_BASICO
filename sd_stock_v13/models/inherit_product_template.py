from odoo import api, fields, models,SUPERUSER_ID,_
# HEREDAMOS EL METODO ONCHANGE PARA RESTRINGIER LOS TIPO DE OPERACION

class InheritSProductTemplateSecuencia(models.Model):
    _inherit = "product.template"

    sd_autor = fields.Many2one('res.partner', string='Autor')

    def action_obtener_siguiente_sequencia(self):
        self.categ_id.sd_secuencia_id.next_by_id()
        number = self.categ_id.sd_siguiente
        self.update({'default_code': number})

