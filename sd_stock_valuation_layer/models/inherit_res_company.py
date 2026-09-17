from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet

class SdInheritResCompany(models.Model):
    _inherit = "res.company"
    sd_management_ids = fields.Many2many('management.company',string="Gestiones", copy=False, readonly=False)

    sd_management_count = fields.Integer(compute='get_count_management_company',store=False,default=0)
    sd_date_ini_management = fields.Datetime(string='Fecha Gestion Inicio',compute='get_date_ini_management',store=False)
    sd_date_end_management = fields.Datetime(string='Fecha Gestion Final',compute='get_date_ini_management',store=False)
    def create_management_company(self):
        if self.env['res.users'].has_group('sd_stock_valuation_layer.sd_grupo_permiso_administrar_management_company'):
            vals = {
                'company_id': [(4, self.id)],
                'sd_date': fields.Datetime.now(),
                'name': 'Borrador',
                'state': 'draft',
            }
            self.env['management.company'].sudo().create(vals)

            return self.action_view_management_company()
        else:
            raise UserError(_("No tiene permiso para realizar este tipo de accion.\nPorfavor consulte a su soporte"))
    def action_view_management_company(self):
        self.ensure_one()
        if len(self.sd_management_ids.ids) != 1:
            return {
                'name': _('Gestion Compañia '+ self.name),
                'view_mode': 'tree,form',
                'res_model': 'management.company',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.sd_management_ids.ids)],
            }
        elif len(self.sd_management_ids.ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'management.company',
                'view_mode': 'form',
                'views': [[self.env.ref('sd_stock_valuation_layer.sd_form_management_company_order').id, 'form']],
                'res_id': self.sd_management_ids.id,
                'target': 'current',
            }
    @api.depends('sd_management_ids')
    def get_count_management_company(self):
        """Contador de cantidad de Gestiones"""
        for company_id in self:
            company_id.sd_management_count = len(company_id.sd_management_ids)
    @api.depends('sd_management_ids.sd_date','sd_management_ids.sd_date_end')
    def get_date_ini_management(self):
        for company_id in self:
            company_id.sd_date_ini_management = company_id.sd_management_ids.search([('state','=','active')],limit=1).sd_date
            company_id.sd_date_end_management = company_id.sd_management_ids.search([('state', '=', 'active')],limit=1).sd_date_end
        