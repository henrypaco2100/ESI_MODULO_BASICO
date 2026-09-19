# -*- coding: utf-8 -*-
# ESI - Especialistas en Sistemas Integrados

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def render_qweb_pdf(self, res_ids=None, data=None):
        """Usa el formato configurado sin exponer permisos ni reportes duplicados.

        La acción visible conserva el Formato 1 y su paperformat. Cuando la compañía
        utiliza Formato 2, la generación se delega a la acción v2 (oculta del menú),
        de modo que también se respeta su paperformat específico.
        """
        self.ensure_one()
        if res_ids:
            move_action = self.env.ref(
                'esi_sd_comprobantes_contable.sd_action_account_move_comprobantes',
                raise_if_not_found=False,
            )
            payment_action = self.env.ref(
                'esi_sd_comprobantes_contable.sd_action_account_payment_comprobantes',
                raise_if_not_found=False,
            )

            if move_action and self.id == move_action.id and self.model == 'account.move':
                docs = self.env['account.move'].browse(res_ids).exists()
                if docs and (docs[0].company_id.esi_comprobante_format or '2') == '2':
                    action_v2 = self.env.ref(
                        'esi_sd_comprobantes_contable.sd_action_account_move_comprobantes_version_2'
                    )
                    return action_v2.with_context(self.env.context).render_qweb_pdf(res_ids=res_ids, data=data)

            if payment_action and self.id == payment_action.id and self.model == 'account.payment':
                docs = self.env['account.payment'].browse(res_ids).exists()
                if docs and (docs[0].company_id.esi_comprobante_format or '2') == '2':
                    action_v2 = self.env.ref(
                        'esi_sd_comprobantes_contable.sd_action_account_payment_version_2'
                    )
                    return action_v2.with_context(self.env.context).render_qweb_pdf(res_ids=res_ids, data=data)

        return super().render_qweb_pdf(res_ids=res_ids, data=data)
