from odoo import fields, models, tools


class SdStockValuationdetailed(models.Model):
    """Valoracion detalla"""

    _name = 'stock.valuation.detailed'

    stock_valuation_id = fields.Many2one('stock.valuation.layer', 'valoracion de stock ', index=True, readonly=True,auto_join=True, ondelete="cascade")
    sd_valuation_purchase_id = fields.Many2one('stock.valuation.layer', 'valoracion de compra')
    sd_value_detailed = fields.Monetary('Valor ', readonly=True)
    sd_qty_detailed = fields.Float(digits=0,string='Cantidad')
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True,
                                  required=True)
    company_id = fields.Many2one('res.company', 'Company', related='stock_valuation_id.company_id',readonly=True, required=True)