# -*- coding: utf-8 -*-
# ESI - Especialistas en Sistemas Integrados

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    esi_comprobante_format = fields.Selection(
        selection=[
            ('1', 'Comprobante 1'),
            ('2', 'Comprobante 2'),
        ],
        string='Formato de Comprobante',
        default='2',
    )

    @api.model
    def _esi_initialize_comprobante_format(self):
        """Asegura Comprobante 2 como formato inicial también en compañías existentes."""
        companies = self.search([('esi_comprobante_format', '=', False)])
        if companies:
            companies.write({'esi_comprobante_format': '2'})

        # Compatibilidad con versiones anteriores: estos grupos ya no son permisos.
        hidden_category = self.env.ref('base.module_category_hidden', raise_if_not_found=False)
        if hidden_category:
            for xmlid in (
                'esi_sd_comprobantes_contable.sd_comprobante_contable_1_group',
                'esi_sd_comprobantes_contable.sd_comprobante_contable_2_group',
            ):
                group = self.env.ref(xmlid, raise_if_not_found=False)
                if group:
                    group.sudo().write({'category_id': hidden_category.id})

        # Si se actualiza una base que ya tenía los reportes protegidos por grupos,
        # retiramos esas restricciones para que el formato dependa de Configuración.
        for xmlid in (
            'esi_sd_comprobantes_contable.sd_action_account_move_comprobantes',
            'esi_sd_comprobantes_contable.sd_action_account_payment_comprobantes',
        ):
            action = self.env.ref(xmlid, raise_if_not_found=False)
            if action:
                action.sudo().write({'groups_id': [(5, 0, 0)]})
        return True


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    esi_comprobante_format = fields.Selection(
        related='company_id.esi_comprobante_format',
        readonly=False,
        string='Formato de Comprobante',
    )
