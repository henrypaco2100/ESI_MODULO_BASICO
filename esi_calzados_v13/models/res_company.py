# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    esi_wip_account_id = fields.Many2one(
        'account.account', string='ESI - Cuenta Producción en Proceso',
        domain="[('company_id', '=', id)]",
        help='Cuenta puente/WIP utilizada para los consumos y la terminación de fabricación.'
    )
    esi_piecework_payable_account_id = fields.Many2one(
        'account.account', string='ESI - Destajos por pagar',
        domain="[('company_id', '=', id)]",
        help='Cuenta acreedora usada al confirmar un destajo.'
    )
    esi_production_journal_id = fields.Many2one(
        'account.journal', string='ESI - Diario de Producción',
        domain="[('company_id', '=', id), ('type', '=', 'general')]",
        help='Diario para asientos de destajos y ajustes de producción ESI.'
    )
