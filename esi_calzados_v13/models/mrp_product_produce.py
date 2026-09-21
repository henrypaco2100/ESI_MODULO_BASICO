# -*- coding: utf-8 -*-
from odoo import models


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def _record_production(self):
        """Después del botón *Producir*, reflejar contablemente el material en proceso.

        En Odoo 13 el wizard ``Producir`` registra cantidades consumidas/producidas,
        pero los movimientos de stock y su valoración se contabilizan recién con
        ``Publicar inventario`` / ``Marcar como hecho``. Para que el Balance muestre
        Producción en Proceso durante ese intervalo, ESI registra una reclasificación
        provisional de Materias Primas -> Producción en Proceso.
        """
        res = super(MrpProductProduce, self)._record_production()
        self.mapped('production_id')._esi_sync_wip_provisional()
        return res
