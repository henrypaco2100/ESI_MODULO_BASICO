from odoo import api, fields, models,SUPERUSER_ID,_
# HEREDAMOS EL METODO ONCHANGE PARA RESTRINGIER LOS TIPO DE OPERACION

class InheritSProductCategorySecuencia(models.Model):
    _inherit = "product.category"

    sd_secuencia_id = fields.Many2one('ir.sequence', string='Secuencia Categoria')
    sd_siguiente = fields.Integer(string='Siguiente Numero', related='sd_secuencia_id.number_next_actual', readonly=False)
    sd_tam_secuencia = fields.Integer(related='sd_secuencia_id.padding', readonly=False)
    sd_name_secuencia = fields.Char(related='sd_secuencia_id.name', readonly=False)

    @api.model
    def create(self, vals):
        res = super(InheritSProductCategorySecuencia, self).create(vals)
        seq_id = self._create_sequence(vals)
        res.update({'sd_secuencia_id': seq_id.id})
        return res

    def _create_sequence(self, vals):
        seq = {'name': vals['name']}
        seq_id = self.env['ir.sequence'].create(seq)
        return seq_id
        
        
