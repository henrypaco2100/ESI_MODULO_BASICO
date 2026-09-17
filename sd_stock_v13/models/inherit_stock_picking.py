from odoo import api, fields, models,SUPERUSER_ID,_
from odoo.addons.stock.models.stock_picking import Picking


# HEREDAMOS EL METODO ONCHANGE PARA RESTRINGIER LOS TIPO DE OPERACION

class InheritStockPickingMejora(models.Model):
    _inherit = "stock.picking"

    sd_porcentaje = fields.Char('Porcentaje')
    sd_cambio_borrador = fields.Boolean(False)
    # sd_es_devolucion = fields.Boolean('Es Devolucion')

    # @api.model
    # def _tipo_picking_filter(self):
    #     reportes = self.env['stock.picking.type'].search([('code', '=', 'internal')])
    #     if reportes:
    #         return reportes.mapped('id')
    #     else:
    #         return []
    # picking_type_id = fields.Many2one(
    #     'stock.picking.type', 'Operation Type',
    #     required=True, readonly=True,
    #     states={'draft': [('readonly', False)]},domain=lambda self: [('id', 'in', self._tipo_picking_filter())])

    @api.onchange('location_id')
    def not_change_location_id(self):
        print('no hace nada')
        # if self.picking_type_id:
        #     if not self.location_id == self.picking_type_id.default_location_src_id:
        #         self.location_id = self.picking_type_id.default_location_src_id
        #         return {'warning': {
        #             'title': 'Advertencia',
        #             'message': 'No puede cambiar la ubicación origen cuando existe el tipo de operación'
        #         }}

    @api.onchange('location_dest_id')
    def not_change_location_dest_id(self):
        print('no hace nada')
        # if self.picking_type_id:
        #     if not self.location_dest_id == self.picking_type_id.default_location_dest_id:
        #         self.location_dest_id = self.picking_type_id.default_location_dest_id
        #         return {'warning': {
        #             'title': 'Advertencia',
        #             'message': 'No puede cambiar la ubicación destino cuando existe el tipo de operación'
        #         }}

    # ESI 2026: se conserva el comportamiento estándar de Odoo para fechas.
    # No se sobreescribe _compute_scheduled_date ni date_done.
    #
    # def create(self, vals):
    #     defaults = self.default_get(['name', 'picking_type_id'])
    #     picking_type = self.env['stock.picking.type'].browse(
    #         vals.get('picking_type_id', defaults.get('picking_type_id')))
    #     vals['name'] = self.env['ir.sequence'].next_by_code('secuencia.borrador')
    #     # if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and vals.get('picking_type_id',
    #     #                                                                                   defaults.get(
    #     #                                                                                           'picking_type_id')):
    #     #     if picking_type.sequence_id:
    #     #         vals['name'] = picking_type.sequence_id.next_by_id()
    #
    #     # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
    #     # As it is a create the format will be a list of (0, 0, dict)
    #     moves = vals.get('move_lines', []) + vals.get('move_ids_without_package', [])
    #     if moves and ((vals.get('location_id') and vals.get('location_dest_id')) or vals.get('partner_id')):
    #         for move in moves:
    #             if len(move) == 3 and move[0] == 0:
    #                 if vals.get('location_id') and vals.get('location_dest_id'):
    #                     move[2]['location_id'] = vals['location_id']
    #                     move[2]['location_dest_id'] = vals['location_dest_id']
    #                     # When creating a new picking, a move can have no `company_id` (create before
    #                     # picking type was defined) or a different `company_id` (the picking type was
    #                     # changed for an another company picking type after the move was created).
    #                     # So, we define the `company_id` in one of these cases.
    #                     picking_type = self.env['stock.picking.type'].browse(vals['picking_type_id'])
    #                     if 'picking_type_id' not in move[2] or move[2]['picking_type_id'] != picking_type.id:
    #                         move[2]['picking_type_id'] = picking_type.id
    #                         move[2]['company_id'] = picking_type.company_id.id
    #                 if vals.get('partner_id'):
    #                     move[2]['partner_id'] = vals.get('partner_id')
    #     # make sure to write `schedule_date` *after* the `stock.move` creation in
    #     # order to get a determinist execution of `_set_scheduled_date`
    #     scheduled_date = vals.pop('scheduled_date', False)
    #     res = super(Picking, self).create(vals)
    #     if scheduled_date:
    #         res.with_context(mail_notrack=True).write({'scheduled_date': scheduled_date})
    #     res._autoconfirm_picking()
    #
    #     # set partner as follower
    #     if vals.get('partner_id'):
    #         for picking in res.filtered(
    #                 lambda p: p.location_id.usage == 'supplier' or p.location_dest_id.usage == 'customer'):
    #             picking.message_subscribe([vals.get('partner_id')])
    #
    #     return res
    #
    # def action_confirm(self):
    #     result = super(InheritStockPickingMejora, self).action_confirm()
    #
    #     defaults = self.default_get(['name', 'picking_type_id'])
    #     picking_type = self.env['stock.picking.type'].browse(self.picking_type_id.id)
    #     print('name: ', self.name)
    #     if self.picking_type_id and not self.sd_cambio_borrador:
    #         # print('entro en el primer if')
    #         if picking_type.sequence_id:
    #             # print('entro en el segundo if')
    #             self.name = picking_type.sequence_id.next_by_id()
    #             self.sd_cambio_borrador = True
    #     return result
    #
    # def button_validate(self):
    #     result = super(InheritStockPickingMejora, self).button_validate()
    #
    #     picking_type = self.env['stock.picking.type'].browse(self.picking_type_id.id)
    #     # print('name: ', self.name)
    #     # print('cambio borrador: ', self.sd_cambio_borrador)
    #     if self.picking_type_id and not self.sd_cambio_borrador:
    #         # print('entro en el primer if')
    #         if picking_type.sequence_id:
    #             # print('entro en el segundo if')
    #             self.name = picking_type.sequence_id.next_by_id()
    #             self.sd_cambio_borrador = True
    #
    #     return result
    #
