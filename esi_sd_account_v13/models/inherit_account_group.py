from odoo import models, fields, api, _

class InheritAccountGroup(models.Model):
    _inherit = 'account.group'

    # sd_codigo = fields.Char('Codigo', required="True")
    sd_analytic_group = fields.Many2one('account.analytic.group', string="Grupo analitico")


class InheritAccountMoveLineAnalyticRelation(models.Model):
    _inherit = 'account.move.line'

    sd_has_analytic_group = fields.Boolean(string="tiene grupo", compute="Sd_analytic_group")
    sd_analytic_group = fields.Many2one('account.analytic.group', string="Grupo analitico", related='account_id.group_id.sd_analytic_group')
    sd_analytic_account_list = fields.Many2one('account.analytic.account', string="lista cuentas analiticas", compute="Sd_analytic_group")
    sd_grupo_financiero = fields.Many2one('account.group',related='account_id.group_id',string='Grupo de Cuentas',store=True)

    @api.depends('account_id')
    def Sd_analytic_group(self):
        for line in self:
            if line.sd_analytic_group:
                line.sd_has_analytic_group = True
                # self.sd_analytic_account_list = self.env['account.analytic.account'].search([('group_id', '=', self.sd_analytic_group)])
            else:
                line.sd_has_analytic_group = False
                # self.sd_analytic_account_list = self.env['account.analytic.account'].search([('company_id', '=', self.account_id.company_id), ('company_id', '!=', False)])
        # print('lista de cuentas: ', self.sd_analytic_account_list)

