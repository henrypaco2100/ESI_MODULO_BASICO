from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet

class ManagementCompany(models.Model):
    _name = "management.company"

    name = fields.Char(string='Nombre', default=lambda self: _('New'))
    company_id = fields.Many2many('res.company',string='Compañia' ,copy=False)
    sd_date = fields.Datetime(string='Fecha Inicial',copy=False)
    sd_date_end = fields.Datetime(string='Fecha Cierre', copy=False)
    sd_description = fields.Text(string='Descripción')
    state = fields.Selection([
        ('draft','Borrador'),
        ('cancel', 'Cancelado'),
        ('active','Activa'),
        ('closed','Finalizada')
    ],strinf='Estado',default='draft')

    def action_confirm_management_active(self):
        """
        Accion para cambiar la gestion a activa o gestion actual
        requisitos: las otroas gestiones deben de estar finalizadas
        """
        if self.env['res.users'].has_group('sd_stock_valuation_layer.sd_grupo_permiso_administrar_management_company'):
            self.comprobar_cierre_otras_gestiones()
            self.write({
                'state':'active'
            })
        else:
            raise UserError(_("No tiene permiso para realizar este tipo de accion.\nPorfavor consulte a su soporte"))
    def action_closed_management(self):
        """
        Accion para cambiar la gestion a finalizada o gestion cierre
        """
        if self.env['res.users'].has_group('sd_stock_valuation_layer.sd_grupo_permiso_administrar_management_company'):
            self.write({
                'state': 'closed',
                'sd_date_end': fields.Datetime.now(),
            })
        else:
            raise UserError(_("No tiene permiso para realizar este tipo de accion.\nPorfavor consulte a su soporte"))
    def action_cancel_management(self):
        """
        Accion para cambiar la gestion a Cancelado o anulada
        """
        if self.env['res.users'].has_group('sd_stock_valuation_layer.sd_grupo_permiso_administrar_management_company'):
            self.write({
                'state': 'cancel',
            })
        else:
            raise UserError(_("No tiene permiso para realizar este tipo de accion.\nPorfavor consulte a su soporte"))
    def comprobar_cierre_otras_gestiones(self):
        """Comprobar Cierre de las otras Gestiones"""
        management_ids = self.env['management.company'].search([('company_id','=',self.company_id.id),('state','=','active')])
        if management_ids:
            raise UserError(_("Existe Una Gestion Activa, para continuar Necesita Cerrar la Gestion Activa/Actual"))


