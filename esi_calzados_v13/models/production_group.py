# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EsiProductionGroup(models.Model):
    _name = 'esi.production.group'
    _description = 'Grupo de órdenes de producción ESI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Referencia', default='Nuevo', copy=False, readonly=True, tracking=True)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True, tracking=True)
    origin = fields.Char(string='Fuente / Origen', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Pedido de venta', ondelete='set null', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', tracking=True)
    salesperson_id = fields.Many2one('res.users', string='Vendedor', tracking=True)
    production_manager_id = fields.Many2one(
        'res.users', string='Encargado de producción', required=True, tracking=True,
        domain="[('share', '=', False)]"
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company, tracking=True
    )
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    line_ids = fields.One2many('esi.production.group.line', 'group_id', string='Productos a fabricar', copy=True)
    production_ids = fields.One2many('mrp.production', 'esi_production_group_id', string='Órdenes de producción')
    production_count = fields.Integer(string='Producciones', compute='_compute_summary')
    bom_count = fields.Integer(string='Listas de materiales', compute='_compute_summary')
    material_move_count = fields.Integer(string='Materiales', compute='_compute_summary')
    material_cost = fields.Monetary(string='Costo materiales', compute='_compute_summary', currency_field='currency_id')
    missing_cost = fields.Monetary(string='Costo faltantes', compute='_compute_summary', currency_field='currency_id')
    other_cost = fields.Monetary(string='Otros costos', compute='_compute_summary', currency_field='currency_id')
    total_estimated_cost = fields.Monetary(string='Costo total estimado', compute='_compute_summary', currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('orders', 'Órdenes creadas'),
        ('done', 'Finalizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)
    notes = fields.Text(string='Observaciones')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('esi.production.group') or _('Nuevo')
        return super(EsiProductionGroup, self).create(vals)

    @api.constrains('line_ids')
    def _check_lines(self):
        for rec in self:
            for line in rec.line_ids:
                if line.product_qty <= 0:
                    raise ValidationError(_('La cantidad a fabricar debe ser mayor a cero.'))

    @api.depends(
        'production_ids', 'production_ids.esi_material_cost', 'production_ids.esi_missing_cost',
        'production_ids.esi_other_cost', 'production_ids.move_raw_ids',
        'line_ids.estimated_material_cost', 'line_ids.bom_id'
    )
    def _compute_summary(self):
        for rec in self:
            productions = rec.production_ids.filtered(lambda p: p.state != 'cancel')
            boms = (productions.mapped('bom_id') | rec.line_ids.mapped('bom_id')).filtered(lambda b: b)
            rec.production_count = len(rec.production_ids)
            rec.bom_count = len(boms)
            rec.material_move_count = len(productions.mapped('move_raw_ids').filtered(lambda m: m.state != 'cancel'))
            if productions:
                material = sum(productions.mapped('esi_material_cost'))
                missing = sum(productions.mapped('esi_missing_cost'))
                other = sum(productions.mapped('esi_other_cost'))
            else:
                material = sum(rec.line_ids.mapped('estimated_material_cost'))
                missing = 0.0
                other = 0.0
            rec.material_cost = material
            rec.missing_cost = missing
            rec.other_cost = other
            # Destajos se manejan como gasto independiente y NO forman parte del costo de producción.
            rec.total_estimated_cost = material + other

    def action_view_productions(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        action['domain'] = [('esi_production_group_id', '=', self.id)]
        action['context'] = {
            'default_esi_production_group_id': self.id,
            'default_user_id': self.production_manager_id.id,
        }
        return action

    def action_view_boms(self):
        self.ensure_one()
        boms = (self.production_ids.mapped('bom_id') | self.line_ids.mapped('bom_id')).filtered(lambda b: b)
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [('id', 'in', boms.ids)]
        return action

    def action_view_materials(self):
        """Muestra en una sola lista todos los materiales de las OF del grupo."""
        self.ensure_one()
        moves = self.production_ids.filtered(lambda p: p.state != 'cancel').mapped('move_raw_ids').filtered(
            lambda m: m.state != 'cancel'
        )
        return {
            'name': _('Materiales del grupo %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
            'context': {'create': False, 'edit': False},
        }

    def _esi_prepare_production_vals(self, line):
        self.ensure_one()
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        vals = {
            'product_id': line.product_id.id,
            'product_qty': line.product_qty,
            'product_uom_id': line.product_uom_id.id,
            'bom_id': line.bom_id.id,
            # Si nació desde Ventas, Odoo mostrará directamente el pedido en Origen.
            # El vínculo al grupo permanece en esi_production_group_id.
            'origin': (self.sale_order_id.name if self.sale_order_id else (self.origin or self.name)),
            'company_id': self.company_id.id,
            'user_id': self.production_manager_id.id,
            'esi_production_group_id': self.id,
            'esi_production_group_line_id': line.id,
        }
        if picking_type:
            vals['picking_type_id'] = picking_type.id
            if picking_type.default_location_src_id:
                vals['location_src_id'] = picking_type.default_location_src_id.id
            if picking_type.default_location_dest_id:
                vals['location_dest_id'] = picking_type.default_location_dest_id.id
        return vals

    def _esi_create_mo_with_onchanges(self, line):
        """Crear la OF usando los onchanges estándar de Odoo 13.

        En Odoo 13 el onchange del producto se llama ``onchange_product_id``
        (sin guion bajo). Después se aplica la LdM y se regeneran explícitamente
        los movimientos de materias primas. De esta forma cada línea del grupo
        crea una OF completa, con sus componentes y variantes correctas.
        """
        Production = self.env['mrp.production'].with_context(
            default_company_id=self.company_id.id,
            force_company=self.company_id.id,
        )
        vals = self._esi_prepare_production_vals(line)
        new_production = Production.new(vals)

        if hasattr(new_production, 'onchange_product_id'):
            new_production.onchange_product_id()

        # Fijamos nuevamente los datos elegidos en el grupo después del onchange.
        new_production.product_id = line.product_id
        new_production.product_qty = line.product_qty
        new_production.product_uom_id = line.product_uom_id
        new_production.bom_id = line.bom_id
        if vals.get('picking_type_id'):
            new_production.picking_type_id = vals['picking_type_id']

        if hasattr(new_production, '_onchange_bom_id'):
            new_production._onchange_bom_id()
        # La LdM puede traer un tipo de operación específico.
        if hasattr(new_production, 'onchange_picking_type') and new_production.picking_type_id:
            new_production.onchange_picking_type()

        # _onchange_bom_id puede restablecer cantidad/UdM según la LdM.
        new_production.product_qty = line.product_qty
        new_production.product_uom_id = line.product_uom_id
        if hasattr(new_production, '_onchange_move_raw'):
            new_production._onchange_move_raw()

        create_vals = new_production._convert_to_write(new_production._cache)
        # Mantener los valores finales de picking/ubicaciones generados por los
        # onchanges y solamente forzar los vínculos ESI y datos del encargo.
        create_vals.update({
            'origin': vals['origin'],
            'company_id': self.company_id.id,
            'user_id': self.production_manager_id.id,
            'esi_production_group_id': self.id,
            'esi_production_group_line_id': line.id,
            'product_id': line.product_id.id,
            'product_qty': line.product_qty,
            'product_uom_id': line.product_uom_id.id,
            'bom_id': line.bom_id.id,
        })
        production = Production.create(create_vals)

        # Respaldo: si una personalización de la base vació los componentes,
        # reconstruimos las líneas en un registro temporal (onchange seguro)
        # y luego las escribimos sobre la OF persistente.
        if not production.move_raw_ids:
            fallback = Production.new(vals)
            if hasattr(fallback, 'onchange_product_id'):
                fallback.onchange_product_id()
            fallback.product_id = line.product_id
            fallback.product_qty = line.product_qty
            fallback.product_uom_id = line.product_uom_id
            fallback.bom_id = line.bom_id
            if hasattr(fallback, '_onchange_bom_id'):
                fallback._onchange_bom_id()
            if hasattr(fallback, 'onchange_picking_type') and fallback.picking_type_id:
                fallback.onchange_picking_type()
            fallback.product_qty = line.product_qty
            fallback.product_uom_id = line.product_uom_id
            if hasattr(fallback, '_onchange_move_raw'):
                fallback._onchange_move_raw()
            raw_commands = fallback._convert_to_write(fallback._cache).get('move_raw_ids')
            if raw_commands:
                production.write({'move_raw_ids': raw_commands})

        if not production.move_raw_ids:
            raise UserError(_(
                'No se pudieron cargar los materiales de la LdM %s para %s. '
                'Revise que la LdM tenga componentes válidos para esta variante.'
            ) % (line.bom_id.display_name, line.product_id.display_name))

        # Captura del costo histórico al crear la OF.
        if hasattr(production.move_raw_ids, 'esi_capture_current_cost'):
            production.move_raw_ids.esi_capture_current_cost(force=False)
        return production

    def action_create_productions(self):
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_('No puede crear órdenes desde un grupo cancelado.'))
            if not rec.production_manager_id:
                raise UserError(_('Seleccione el Encargado de producción.'))
            if not rec.line_ids:
                raise UserError(_('Agregue al menos un producto a fabricar.'))

            missing_bom = rec.line_ids.filtered(lambda l: not l.bom_id or not l.bom_id.bom_line_ids)
            if missing_bom:
                raise UserError(_(
                    'No se pueden crear las órdenes. Los siguientes productos no tienen una Lista de Materiales completa:\n- %s\n\n'
                    'Use el botón LdM de cada línea para crear o editar su lista de materiales.'
                ) % '\n- '.join(missing_bom.mapped('product_id.display_name')))

            created = self.env['mrp.production']
            for line in rec.line_ids:
                if line.production_id and line.production_id.state != 'cancel':
                    continue
                production = rec._esi_create_mo_with_onchanges(line)
                line.production_id = production.id
                created |= production
            if created or rec.production_ids:
                rec.state = 'orders'
        return self.action_view_productions() if len(self) == 1 else True

    def action_refresh_from_sale(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('Este grupo no está relacionado con un pedido de venta.'))
        if self.production_ids:
            raise UserError(_('No se pueden recalcular faltantes porque el grupo ya tiene órdenes de producción creadas.'))
        self.line_ids.unlink()
        self.sale_order_id._esi_fill_production_group_shortages(self)
        return True

    def action_mark_done(self):
        for rec in self:
            if rec.production_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                raise UserError(_('Aún existen órdenes de producción del grupo que no están finalizadas.'))
            rec.state = 'done'
        return True

    def action_cancel(self):
        for rec in self:
            active = rec.production_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if active:
                raise UserError(_('Cancele primero las órdenes de producción abiertas del grupo.'))
            rec.state = 'cancel'
        return True


class EsiProductionGroupLine(models.Model):
    _name = 'esi.production.group.line'
    _description = 'Línea de grupo de producción ESI'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    group_id = fields.Many2one('esi.production.group', string='Grupo', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='group_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Producto / Variante', required=True,
        domain="[('type', '=', 'product')]"
    )
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id', string='Plantilla de producto', store=True, readonly=True
    )
    variant_info = fields.Char(string='Variante', compute='_compute_variant_info')
    product_qty = fields.Float(string='Cantidad', default=1.0, required=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='UdM', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Lista de materiales')
    bom_ready = fields.Boolean(string='LdM lista', compute='_compute_costs')
    estimated_material_cost = fields.Monetary(
        string='Costo materiales estimado', compute='_compute_costs', currency_field='currency_id'
    )
    production_id = fields.Many2one('mrp.production', string='Orden de producción', readonly=True, copy=False, ondelete='set null')

    @api.depends('product_id', 'product_id.product_template_attribute_value_ids')
    def _compute_variant_info(self):
        for line in self:
            values = line.product_id.product_template_attribute_value_ids
            line.variant_info = ' | '.join(
                '%s: %s' % (value.attribute_id.name, value.name) for value in values
            ) if values else ''

    def _esi_find_bom(self, product=None):
        self.ensure_one()
        product = product or self.product_id
        if not product:
            return self.env['mrp.bom']
        Bom = self.env['mrp.bom']
        company = self.company_id or self.env.company
        try:
            bom = Bom._bom_find(product=product, company_id=company.id, bom_type='normal')
            if bom:
                return bom
        except Exception:
            pass
        exact = Bom.search([
            ('product_id', '=', product.id),
            ('type', '=', 'normal'),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ], limit=1)
        if exact:
            return exact
        return Bom.search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('product_id', '=', False),
            ('type', '=', 'normal'),
            '|', ('company_id', '=', company.id), ('company_id', '=', False),
        ], limit=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.bom_id = self._esi_find_bom(self.product_id)

    @api.constrains('product_id', 'bom_id')
    def _check_bom_product(self):
        for line in self:
            if not line.product_id or not line.bom_id:
                continue
            bom = line.bom_id
            valid_template = bom.product_tmpl_id == line.product_id.product_tmpl_id
            valid_variant = not bom.product_id or bom.product_id == line.product_id
            if bom.type != 'normal' or not valid_template or not valid_variant:
                raise ValidationError(_(
                    'La Lista de Materiales %s no corresponde a la variante %s.'
                ) % (bom.display_name, line.product_id.display_name))

    def _esi_bom_line_applies(self, bom_line):
        self.ensure_one()
        field_name = 'bom_product_template_attribute_value_ids'
        if field_name in bom_line._fields:
            required_values = bom_line[field_name]
            if required_values:
                product_values = self.product_id.product_template_attribute_value_ids
                if required_values - product_values:
                    return False
        return True

    def _esi_bom_material_cost(self):
        self.ensure_one()
        bom = self.bom_id
        if not bom or not bom.bom_line_ids or not self.product_qty or not self.product_uom_id:
            return 0.0

        # Usar explode() es importante en calzado: respeta componentes que aplican
        # solamente a determinadas variantes (talla/color) y sub-LdM fantasma.
        factor = self.product_uom_id._compute_quantity(
            self.product_qty, bom.product_uom_id
        ) / (bom.product_qty or 1.0)
        total = 0.0
        try:
            _boms, exploded_lines = bom.explode(
                self.product_id, factor,
                picking_type=bom.picking_type_id,
            )
        except Exception:
            exploded_lines = []

        if exploded_lines:
            for bom_line, line_data in exploded_lines:
                component = bom_line.product_id.sudo().with_context(force_company=self.company_id.id)
                qty = line_data.get('qty', 0.0)
                line_uom = bom_line.product_uom_id
                unit_cost = component.standard_price or 0.0
                if line_uom and component.uom_id and line_uom != component.uom_id and line_uom.category_id == component.uom_id.category_id:
                    unit_cost = component.uom_id._compute_price(unit_cost, line_uom)
                total += qty * unit_cost
            return total

        # Fallback para bases con personalizaciones de MRP que modifiquen explode().
        for bom_line in bom.bom_line_ids:
            if not self._esi_bom_line_applies(bom_line):
                continue
            component = bom_line.product_id.sudo().with_context(force_company=self.company_id.id)
            qty = (bom_line.product_qty or 0.0) * factor
            unit_cost = component.standard_price or 0.0
            line_uom = bom_line.product_uom_id
            if line_uom and component.uom_id and line_uom != component.uom_id and line_uom.category_id == component.uom_id.category_id:
                unit_cost = component.uom_id._compute_price(unit_cost, line_uom)
            total += qty * unit_cost
        return total

    @api.depends('product_id', 'product_qty', 'product_uom_id', 'bom_id', 'bom_id.bom_line_ids', 'production_id.esi_material_cost')
    def _compute_costs(self):
        for line in self:
            line.bom_ready = bool(line.bom_id and line.bom_id.bom_line_ids)
            if line.production_id and line.production_id.state != 'cancel':
                line.estimated_material_cost = line.production_id.esi_material_cost
            else:
                line.estimated_material_cost = line._esi_bom_material_cost() if line.product_id and line.product_uom_id else 0.0

    def action_open_bom(self):
        self.ensure_one()
        if not self.product_id:
            raise UserError(_('Seleccione primero un producto.'))
        bom = self.bom_id or self._esi_find_bom(self.product_id)
        if not bom:
            vals = {
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'product_qty': 1.0,
                'product_uom_id': self.product_id.uom_id.id,
                'type': 'normal',
                'company_id': self.company_id.id,
                'code': 'ESI %s' % (self.product_id.default_code or self.product_id.display_name),
            }
            if 'product_id' in self.env['mrp.bom']._fields and len(self.product_id.product_tmpl_id.product_variant_ids) > 1:
                vals['product_id'] = self.product_id.id
            bom = self.env['mrp.bom'].create(vals)
            self.bom_id = bom.id
        else:
            self.bom_id = bom.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lista de materiales'),
            'res_model': 'mrp.bom',
            'res_id': bom.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_production(self):
        self.ensure_one()
        if not self.production_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orden de producción'),
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
