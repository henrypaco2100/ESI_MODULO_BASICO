# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EsiCalzadosDemoLoader(models.TransientModel):
    _name = 'esi.calzados.demo.loader'
    _description = 'ESI - Cargar demo de calzados'

    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id
    )
    create_manufacturing_orders = fields.Boolean(
        string='Crear 3 órdenes de fabricación', default=True
    )
    result = fields.Text(string='Resultado', readonly=True)

    # ------------------------------------------------------------------
    # Helpers genéricos
    # ------------------------------------------------------------------
    def _ref(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    def _account_type(self, xmlid, fallback=None):
        rec = self._ref(xmlid)
        if not rec and fallback:
            rec = self._ref(fallback)
        if not rec:
            raise UserError(_('No se encontró el tipo de cuenta requerido: %s') % xmlid)
        return rec

    def _get_or_create_account(self, company, code, name, type_xmlid, reconcile=False, fallback=None):
        Account = self.env['account.account'].sudo().with_context(force_company=company.id)
        account = Account.search([('company_id', '=', company.id), ('code', '=', code)], limit=1)
        if account:
            return account
        return Account.create({
            'code': code,
            'name': name,
            'user_type_id': self._account_type(type_xmlid, fallback).id,
            'company_id': company.id,
            'reconcile': reconcile,
        })

    def _get_or_create_journal(self, company):
        Journal = self.env['account.journal'].sudo().with_context(force_company=company.id)
        journal = Journal.search([('company_id', '=', company.id), ('code', '=', 'ESIPR')], limit=1)
        if journal:
            return journal
        return Journal.create({
            'name': 'Valoración Producción ESI',
            'code': 'ESIPR',
            'type': 'general',
            'company_id': company.id,
        })

    def _get_or_create_category(self, company, name, valuation_account, stock_input,
                                stock_output, journal, income_account, expense_account):
        Category = self.env['product.category'].sudo().with_context(force_company=company.id)
        category = Category.search([('name', '=', name)], limit=1)
        if not category:
            category = Category.create({'name': name})
        vals = {
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': valuation_account.id,
            'property_stock_account_input_categ_id': stock_input.id,
            'property_stock_account_output_categ_id': stock_output.id,
            'property_stock_journal': journal.id,
        }
        if 'property_account_income_categ_id' in category._fields:
            vals['property_account_income_categ_id'] = income_account.id
        if 'property_account_expense_categ_id' in category._fields:
            vals['property_account_expense_categ_id'] = expense_account.id
        category.with_context(force_company=company.id).sudo().write(vals)
        return category

    def _get_or_create_uom(self, category_name, uom_name, rounding=0.01):
        Cat = self.env['uom.category'].sudo()
        Uom = self.env['uom.uom'].sudo()
        category = Cat.search([('name', '=', category_name)], limit=1)
        if not category:
            category = Cat.create({'name': category_name})
        uom = Uom.search([('name', '=', uom_name), ('category_id', '=', category.id)], limit=1)
        if not uom:
            vals = {
                'name': uom_name,
                'category_id': category.id,
                'uom_type': 'reference',
                'factor': 1.0,
                'rounding': rounding,
            }
            # Odoo 13 posee measure_type en algunas instalaciones/módulos.
            if 'measure_type' in Uom._fields:
                vals['measure_type'] = 'unit'
            uom = Uom.create(vals)
        return uom

    def _get_or_create_attribute(self, preferred_name, fallback_name, values):
        Attribute = self.env['product.attribute'].sudo()
        Value = self.env['product.attribute.value'].sudo()

        attr = Attribute.search([('name', '=', preferred_name)], limit=1)
        # Si ya existe un atributo con el nombre estándar pero está configurado
        # como "Nunca crear variantes", no lo modificamos si ya está usado.
        if attr and attr.create_variant == 'no_variant' and attr.is_used_on_products:
            attr = Attribute.search([('name', '=', fallback_name)], limit=1)
            if not attr:
                attr = Attribute.create({'name': fallback_name, 'create_variant': 'always'})
        elif not attr:
            attr = Attribute.create({'name': preferred_name, 'create_variant': 'always'})
        elif attr.create_variant != 'always' and not attr.is_used_on_products:
            attr.write({'create_variant': 'always'})

        result = {}
        for value_name in values:
            val = Value.search([('attribute_id', '=', attr.id), ('name', '=', value_name)], limit=1)
            if not val:
                val = Value.create({'attribute_id': attr.id, 'name': value_name})
            result[value_name] = val
        return attr, result

    def _ensure_template_attribute_line(self, tmpl, attr, values):
        Line = self.env['product.template.attribute.line'].sudo()
        line = Line.search([
            ('product_tmpl_id', '=', tmpl.id),
            ('attribute_id', '=', attr.id),
        ], limit=1)
        vals = {'value_ids': [(6, 0, [v.id for v in values])]}
        if line:
            line.write(vals)
        else:
            vals.update({'product_tmpl_id': tmpl.id, 'attribute_id': attr.id})
            line = Line.create(vals)
        return line

    def _get_or_create_analytic(self, company, name, code):
        """Crea/actualiza una cuenta analítica compatible con ESI_MODULO_BASICO.

        El módulo esi_sd_account_v13 agrega el campo obligatorio ``sd_codigo``
        a account.analytic.account. En una base sin ese módulo el campo no existe,
        por eso se completa de forma dinámica solamente cuando está disponible.
        """
        Analytic = self.env['account.analytic.account'].sudo().with_context(force_company=company.id)
        rec = Analytic.search([('name', '=', name), ('company_id', 'in', [False, company.id])], limit=1)
        vals = {'name': name, 'company_id': company.id}
        if 'code' in Analytic._fields:
            vals['code'] = code
        # Compatibilidad con ESI_MODULO_BASICO / esi_sd_account_v13.
        # Ese módulo define sd_codigo como required=True y a nivel SQL termina
        # existiendo como NOT NULL en bases donde ya fue aplicado.
        if 'sd_codigo' in Analytic._fields:
            vals['sd_codigo'] = code
        if rec:
            rec.write(vals)
        else:
            rec = Analytic.create(vals)
        return rec

    def _get_or_create_finished_template(self, company, name, code, category, uom,
                                         sale_price, analytic, talla_attr, talla_values,
                                         color_attr, color_values):
        Tmpl = self.env['product.template'].sudo().with_context(force_company=company.id)
        tmpl = Tmpl.search([('name', '=', name), ('company_id', 'in', [False, company.id])], limit=1)
        vals = {
            'name': name,
            'type': 'product',
            'categ_id': category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
            'list_price': sale_price,
            'company_id': company.id,
            'sale_ok': True,
            'purchase_ok': False,
            'esi_production_analytic_account_id': analytic.id,
        }
        # default_code en template solo es estable si existe una variante. Se
        # aplicará también después sobre las variantes demo.
        if tmpl:
            tmpl.write(vals)
        else:
            vals['default_code'] = code
            tmpl = Tmpl.create(vals)

        self._ensure_template_attribute_line(tmpl, talla_attr, talla_values)
        self._ensure_template_attribute_line(tmpl, color_attr, color_values)
        tmpl._create_variant_ids()
        return tmpl

    def _get_or_create_partner(self, name, supplier=False):
        Partner = self.env['res.partner'].sudo()
        rec = Partner.search([('name', '=', name)], limit=1)
        vals = {'name': name, 'company_type': 'person'}
        if supplier and 'supplier_rank' in Partner._fields:
            vals['supplier_rank'] = 1
        if rec:
            rec.write(vals)
        else:
            rec = Partner.create(vals)
        return rec

    def _get_or_create_raw_product(self, company, name, code, category, uom, cost, vendor):
        Tmpl = self.env['product.template'].sudo().with_context(force_company=company.id)
        tmpl = Tmpl.search([('default_code', '=', code), ('company_id', 'in', [False, company.id])], limit=1)
        vals = {
            'name': name,
            'type': 'product',
            'categ_id': category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
            'standard_price': cost,
            'default_code': code,
            'company_id': company.id,
            'purchase_ok': True,
            'sale_ok': False,
        }
        if tmpl:
            tmpl.write(vals)
        else:
            tmpl = Tmpl.create(vals)
        product = tmpl.product_variant_id

        Supplier = self.env['product.supplierinfo'].sudo()
        seller = Supplier.search([
            ('name', '=', vendor.id),
            ('product_tmpl_id', '=', tmpl.id),
        ], limit=1)
        svals = {
            'name': vendor.id,
            'product_tmpl_id': tmpl.id,
            'min_qty': 0.0,
            'price': cost,
        }
        if 'company_id' in Supplier._fields:
            svals['company_id'] = company.id
        if seller:
            seller.write(svals)
        else:
            Supplier.create(svals)
        return product

    def _ptav(self, tmpl, attr, value_name):
        line = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == attr)[:1]
        if not line:
            return self.env['product.template.attribute.value']
        return line.product_template_value_ids.filtered(lambda v: v.name == value_name)

    def _get_or_create_bom(self, company, tmpl, code, lines):
        Bom = self.env['mrp.bom'].sudo().with_context(force_company=company.id)
        BomLine = self.env['mrp.bom.line'].sudo().with_context(force_company=company.id)
        bom = Bom.search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
        vals = {
            'code': code,
            'product_tmpl_id': tmpl.id,
            'product_qty': 1.0,
            'product_uom_id': tmpl.uom_id.id,
            'type': 'normal',
            'company_id': company.id,
            'consumption': 'flexible',
        }
        if bom:
            # No borramos líneas si ya existen OF activas. Actualizamos la cabecera
            # y reconstruimos solo cuando todavía no se usó la LdM.
            bom.write(vals)
            has_mo = self.env['mrp.production'].sudo().search_count([('bom_id', '=', bom.id)])
            if not has_mo:
                bom.bom_line_ids.unlink()
            else:
                return bom
        else:
            bom = Bom.create(vals)

        for item in lines:
            product, qty, group = item[:3]
            bvals = {
                'bom_id': bom.id,
                'product_id': product.id,
                'product_qty': qty,
                'product_uom_id': product.uom_id.id,
                'esi_material_group': group,
            }
            if len(item) > 3 and item[3]:
                bvals['bom_product_template_attribute_value_ids'] = [(6, 0, item[3].ids)]
            BomLine.create(bvals)
        return bom

    def _variant(self, tmpl, talla_name, color_name, code):
        variants = tmpl.product_variant_ids
        for variant in variants:
            values = variant.product_template_attribute_value_ids.mapped('name')
            if talla_name in values and color_name in values:
                variant.default_code = code
                return variant
        variant = variants[:1]
        if variant:
            variant.default_code = code
        return variant

    def _get_or_create_activity(self, company, code, name, rate, sequence):
        Model = self.env['esi.calzado.destajo.actividad'].sudo()
        rec = Model.search([('company_id', '=', company.id), ('code', '=', code)], limit=1)
        vals = {
            'company_id': company.id,
            'code': code,
            'name': name,
            'default_unit_price': rate,
            'sequence': sequence,
        }
        if rec:
            rec.write(vals)
        else:
            rec = Model.create(vals)
        return rec

    def _get_or_create_mo(self, company, product, bom, qty, analytic, origin):
        """Crea/repara una OF demo con sus componentes antes de confirmar.

        En Odoo 13, crear ``mrp.production`` por ORM con ``bom_id`` no ejecuta
        automáticamente el onchange que genera ``move_raw_ids``. Si se llama
        ``action_confirm`` inmediatamente, Odoo muestra:
        "Agregue algunos materiales a consumir antes de marcar esta OP por hacer".

        Esta rutina también repara OF demo que hayan quedado en borrador por un
        intento anterior fallido.
        """
        Production = self.env['mrp.production'].sudo().with_context(
            default_company_id=company.id, force_company=company.id
        )
        mo = Production.search([('origin', '=', origin), ('company_id', '=', company.id)], limit=1)

        vals = {
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': product.uom_id.id,
            'bom_id': bom.id,
            'company_id': company.id,
            'origin': origin,
            'esi_analytic_account_id': analytic.id,
        }

        if mo:
            # Si un intento anterior dejó la OF en borrador sin componentes,
            # actualizamos cabecera y reconstruimos las líneas desde la LdM.
            if mo.state == 'draft':
                mo.write(vals)
        else:
            # Odoo 13 usa este contexto en create() para disparar
            # _onchange_move_raw(), exactamente como al importar una OF.
            mo = Production.with_context(import_file=True).create(vals)

        if mo.state == 'draft':
            if not mo.move_raw_ids:
                mo._onchange_move_raw()

            # Respaldo explícito: algunas personalizaciones pueden interferir con
            # el onchange. En ese caso generamos directamente los movimientos
            # de componentes usando el método estándar de Odoo 13.
            if not mo.move_raw_ids and mo.bom_id:
                move_vals = mo._get_moves_raw_values()
                if move_vals:
                    self.env['stock.move'].sudo().create(move_vals)

            if not mo.move_raw_ids:
                raise UserError(_(
                    'La OF demo %s no pudo generar materiales desde la LdM %s. '
                    'Revise que la LdM tenga componentes aplicables a la variante %s.'
                ) % (origin, bom.display_name, product.display_name))

            mo.action_confirm()

        return mo

    def _create_destajo(self, mo, worker, activity, qty, rate, description, pair_uom):
        Destajo = self.env['esi.calzado.destajo'].sudo()
        rec = Destajo.search([
            ('production_id', '=', mo.id),
            ('partner_id', '=', worker.id),
            ('activity_id', '=', activity.id),
            ('description', '=', description),
        ], limit=1)
        if rec:
            return rec
        return Destajo.create({
            'production_id': mo.id,
            'partner_id': worker.id,
            'activity_id': activity.id,
            'description': description,
            'quantity': qty,
            'uom_id': pair_uom.id,
            'unit_price': rate,
            'date': fields.Date.context_today(self),
            'state': 'draft',
        })

    @api.model
    def auto_load_demo(self):
        """Carga automática usada por XML al instalar o actualizar el módulo.

        A diferencia de la versión anterior, no deja el módulo instalado vacío:
        si la carga no puede completarse, la instalación/actualización mostrará
        el error real y hará rollback, evitando una falsa instalación sin datos.
        """
        company = self.env.user.company_id or self.env.company
        wizard = self.create({
            'company_id': company.id,
            'create_manufacturing_orders': True,
        })
        wizard.action_load_demo()
        return True

    # ------------------------------------------------------------------
    # Carga demo
    # ------------------------------------------------------------------
    def action_load_demo(self):
        self.ensure_one()
        company = self.company_id
        try:
            # 1) CUENTAS / VALORACIÓN AUTOMÁTICA
            raw_account = self._get_or_create_account(
                company, '153000', 'Materias primas',
                'account.data_account_type_current_assets')
            wip_account = self._get_or_create_account(
                company, '154000', 'Producción en Proceso',
                'account.data_account_type_current_assets')
            finished_account = self._get_or_create_account(
                company, '155000', 'Productos terminados',
                'account.data_account_type_current_assets')
            stock_input = self._get_or_create_account(
                company, '214001', 'Materiales recibidos pendientes de facturar',
                'account.data_account_type_current_liabilities', reconcile=True)
            stock_output = self._get_or_create_account(
                company, '158001', 'Materiales entregados pendientes de facturar',
                'account.data_account_type_current_assets', reconcile=True)
            piecework_payable = self._get_or_create_account(
                company, '215500', 'Destajos por pagar - Producción',
                'account.data_account_type_current_liabilities', reconcile=True)
            income = self._get_or_create_account(
                company, '411010', 'Ventas de productos terminados',
                'account.data_account_type_revenue')
            expense = self._get_or_create_account(
                company, '611010', 'Costo de productos terminados vendidos',
                'account.data_account_type_expenses')
            journal = self._get_or_create_journal(company)

            company.sudo().write({
                'esi_wip_account_id': wip_account.id,
                'esi_piecework_payable_account_id': piecework_payable.id,
                'esi_production_journal_id': journal.id,
            })

            production_location = self._ref('stock.stock_location_production')
            if not production_location:
                production_location = self.env['stock.location'].sudo().search([('usage', '=', 'production')], limit=1)
            if not production_location:
                raise UserError(_('No se encontró la ubicación virtual Producción de Odoo.'))
            production_location.sudo().write({
                'valuation_in_account_id': wip_account.id,
                'valuation_out_account_id': wip_account.id,
            })

            raw_cat = self._get_or_create_category(
                company, 'ESI DEMO - Materias Primas AVCO', raw_account,
                stock_input, stock_output, journal, income, expense)
            finished_cat = self._get_or_create_category(
                company, 'ESI DEMO - Producto Terminado AVCO', finished_account,
                stock_input, stock_output, journal, income, expense)

            # 2) UDM / ATRIBUTOS / ANALÍTICAS
            pair_uom = self._get_or_create_uom('Calzado ESI', 'Par', 1.0)
            ft2_uom = self._get_or_create_uom('Área ESI', 'ft²', 0.01)
            unit_uom = self._ref('uom.product_uom_unit') or self.env['uom.uom'].sudo().search([], limit=1)
            meter_uom = self._ref('uom.product_uom_meter') or unit_uom
            gram_uom = self._ref('uom.product_uom_gram') or unit_uom

            talla_attr, talla = self._get_or_create_attribute(
                'Talla', 'Talla ESI', ['39', '40', '41', '42', '43'])
            color_attr, color = self._get_or_create_attribute(
                'Color', 'Color ESI', ['Negro', 'Café', 'Beige'])

            aa_lona = self._get_or_create_analytic(company, 'Producción - Bota Lona', 'CALZ-LONA')
            aa_cuero = self._get_or_create_analytic(company, 'Producción - Bota Puro Cuero', 'CALZ-CUERO')
            aa_tenis = self._get_or_create_analytic(company, 'Producción - Tenis Táctico', 'CALZ-TENIS')

            bota_lona = self._get_or_create_finished_template(
                company, 'Bota Lona ESI Demo', 'PT-BLONA', finished_cat, pair_uom,
                280.0, aa_lona, talla_attr, [talla['40'], talla['41'], talla['42']],
                color_attr, [color['Negro'], color['Café']])
            bota_cuero = self._get_or_create_finished_template(
                company, 'Bota Puro Cuero ESI Demo', 'PT-BCUERO', finished_cat, pair_uom,
                420.0, aa_cuero, talla_attr, [talla['40'], talla['41'], talla['42'], talla['43']],
                color_attr, [color['Negro'], color['Café']])
            tenis = self._get_or_create_finished_template(
                company, 'Tenis Táctico ESI Demo', 'PT-TTACT', finished_cat, pair_uom,
                320.0, aa_tenis, talla_attr, [talla['39'], talla['40'], talla['41'], talla['42']],
                color_attr, [color['Negro'], color['Beige']])

            # 3) MATERIALES
            vendor = self._get_or_create_partner('Proveedor Materiales Calzado ESI Demo', supplier=True)
            defs = [
                ('cuero_hunting', 'Cuero Hunting', ft2_uom, 14.00, 'MP-CUERO-H'),
                ('lona', 'Lona', meter_uom, 44.00, 'MP-LONA'),
                ('lobo_marino', 'Lobo Marino', meter_uom, 35.00, 'MP-LOBO'),
                ('fibra', 'Fibra espuma', meter_uom, 15.00, 'MP-FIBRA'),
                ('cinta25', 'Cinta 2.5', meter_uom, 1.20, 'MP-CINTA25'),
                ('cinta5', 'Cinta 5 cm', meter_uom, 1.60, 'MP-CINTA5'),
                ('plantilla', 'Plantilla costra', ft2_uom, 8.50, 'MP-PLANT'),
                ('contrafuerte', 'Contrafuerte talón termoplástico', ft2_uom, 30.00, 'MP-CONTRA'),
                ('tubox_talon', 'Tubox talón', meter_uom, 13.00, 'MP-TUBT'),
                ('tubox_puntera', 'Tubox puntera', meter_uom, 13.00, 'MP-TUBP'),
                ('puntera', 'Puntera termoplástico', ft2_uom, 89.00, 'MP-PUNTA'),
                ('hilo', 'Hilo 40 negro/beige', gram_uom, 0.44, 'MP-HILO40'),
                ('ojalillos', 'Ojalillos', unit_uom, 0.03, 'MP-OJAL'),
                ('cordon', 'Cordón calzado', pair_uom, 2.50, 'MP-CORDON'),
                ('pegamento', 'Pegamento', gram_uom, 0.06, 'MP-PEG'),
                ('suela40', 'Suela Bota T40', pair_uom, 31.00, 'MP-SUELA40'),
                ('suela41', 'Suela Bota T41', pair_uom, 32.00, 'MP-SUELA41'),
                ('suela42', 'Suela Bota T42', pair_uom, 33.00, 'MP-SUELA42'),
                ('suela43', 'Suela Bota T43', pair_uom, 34.00, 'MP-SUELA43'),
                ('suela_tenis', 'Suela Tenis Táctico', pair_uom, 29.00, 'MP-STENIS'),
                ('sintetico', 'Suede / Sintético', ft2_uom, 11.50, 'MP-SINT'),
                ('forro', 'Tocuyo / Forro', meter_uom, 7.50, 'MP-FORRO'),
            ]
            mats = {}
            for key, name, uom, cost, code in defs:
                mats[key] = self._get_or_create_raw_product(
                    company, name, code, raw_cat, uom, cost, vendor)

            # 4) LdM + VARIANTES
            bl40 = self._ptav(bota_lona, talla_attr, '40')
            bl41 = self._ptav(bota_lona, talla_attr, '41')
            bl42 = self._ptav(bota_lona, talla_attr, '42')
            bc40 = self._ptav(bota_cuero, talla_attr, '40')
            bc41 = self._ptav(bota_cuero, talla_attr, '41')
            bc42 = self._ptav(bota_cuero, talla_attr, '42')
            bc43 = self._ptav(bota_cuero, talla_attr, '43')

            bom_lona = self._get_or_create_bom(company, bota_lona, 'BOM-ESI-BLONA', [
                (mats['cuero_hunting'], 1.90, 'structure'),
                (mats['lona'], 0.15, 'structure'),
                (mats['lobo_marino'], 0.18, 'structure'),
                (mats['fibra'], 0.02, 'structure'),
                (mats['cinta25'], 0.73, 'structure'),
                (mats['cinta5'], 0.40, 'structure'),
                (mats['plantilla'], 0.50, 'structure'),
                (mats['contrafuerte'], 0.03, 'structure'),
                (mats['tubox_talon'], 0.03, 'structure'),
                (mats['tubox_puntera'], 0.02, 'structure'),
                (mats['puntera'], 0.02, 'structure'),
                (mats['hilo'], 0.60, 'utensils'),
                (mats['ojalillos'], 12.0, 'utensils'),
                (mats['cordon'], 1.0, 'utensils'),
                (mats['pegamento'], 12.0, 'utensils'),
                (mats['suela40'], 1.0, 'structure', bl40),
                (mats['suela41'], 1.0, 'structure', bl41),
                (mats['suela42'], 1.0, 'structure', bl42),
            ])
            bom_cuero = self._get_or_create_bom(company, bota_cuero, 'BOM-ESI-BCUERO', [
                (mats['cuero_hunting'], 2.35, 'structure'),
                (mats['forro'], 0.38, 'structure'),
                (mats['fibra'], 0.03, 'structure'),
                (mats['contrafuerte'], 0.04, 'structure'),
                (mats['puntera'], 0.025, 'structure'),
                (mats['plantilla'], 0.55, 'structure'),
                (mats['hilo'], 0.75, 'utensils'),
                (mats['ojalillos'], 14.0, 'utensils'),
                (mats['cordon'], 1.0, 'utensils'),
                (mats['pegamento'], 15.0, 'utensils'),
                (mats['suela40'], 1.0, 'structure', bc40),
                (mats['suela41'], 1.0, 'structure', bc41),
                (mats['suela42'], 1.0, 'structure', bc42),
                (mats['suela43'], 1.0, 'structure', bc43),
            ])
            bom_tenis = self._get_or_create_bom(company, tenis, 'BOM-ESI-TTACT', [
                (mats['sintetico'], 1.45, 'structure'),
                (mats['lona'], 0.22, 'structure'),
                (mats['fibra'], 0.05, 'structure'),
                (mats['forro'], 0.30, 'structure'),
                (mats['plantilla'], 0.45, 'structure'),
                (mats['hilo'], 0.55, 'utensils'),
                (mats['ojalillos'], 10.0, 'utensils'),
                (mats['cordon'], 1.0, 'utensils'),
                (mats['pegamento'], 10.0, 'utensils'),
                (mats['suela_tenis'], 1.0, 'structure'),
            ])

            # 5) DESTAJOS / 3 OF
            corte = self._get_or_create_activity(company, 'CORTE', 'Corte', 1.20, 10)
            aparado = self._get_or_create_activity(company, 'APARADO', 'Aparado', 2.00, 20)
            armado = self._get_or_create_activity(company, 'ARMADO', 'Armado', 1.50, 30)
            acabado = self._get_or_create_activity(company, 'ACABADO', 'Acabado', 0.90, 40)

            emilio = self._get_or_create_partner('Emilio Barrera')
            edith = self._get_or_create_partner('Edith Poma')
            carlos = self._get_or_create_partner('Carlos Mamani')

            mo_count = 0
            destajo_count = 0
            if self.create_manufacturing_orders:
                prod_lona = self._variant(bota_lona, '42', 'Negro', 'PT-BLONA-42-N')
                prod_cuero = self._variant(bota_cuero, '41', 'Café', 'PT-BCUERO-41-C')
                prod_tenis = self._variant(tenis, '40', 'Negro', 'PT-TTACT-40-N')
                if not (prod_lona and prod_cuero and prod_tenis):
                    raise UserError(_('No fue posible generar las variantes de los productos terminados.'))

                mo1 = self._get_or_create_mo(company, prod_lona, bom_lona, 50.0, aa_lona, 'DEMO-ESI-CALZADO-01')
                mo2 = self._get_or_create_mo(company, prod_cuero, bom_cuero, 40.0, aa_cuero, 'DEMO-ESI-CALZADO-02')
                mo3 = self._get_or_create_mo(company, prod_tenis, bom_tenis, 60.0, aa_tenis, 'DEMO-ESI-CALZADO-03')
                mo_count = 3

                destajos = [
                    (mo1, emilio, corte, 50.0, 1.20, 'Corte piezas Bota Lona'),
                    (mo1, edith, aparado, 50.0, 2.00, 'Aparado Bota Lona'),
                    (mo1, carlos, armado, 50.0, 1.50, 'Armado Bota Lona'),
                    (mo2, emilio, corte, 40.0, 1.45, 'Corte cuero'),
                    (mo2, edith, aparado, 40.0, 2.30, 'Aparado cuero'),
                    (mo2, carlos, acabado, 40.0, 1.10, 'Acabado Bota Puro Cuero'),
                    (mo3, emilio, corte, 60.0, 1.00, 'Corte sintético'),
                    (mo3, edith, aparado, 60.0, 1.80, 'Aparado Tenis Táctico'),
                    (mo3, carlos, acabado, 60.0, 0.90, 'Acabado Tenis Táctico'),
                ]
                for vals in destajos:
                    self._create_destajo(*(vals + (pair_uom,)))
                destajo_count = len(destajos)

            # Fuerza recaptura de costos de las OF demo si existen.
            demo_mos = self.env['mrp.production'].sudo().search([
                ('origin', 'in', ['DEMO-ESI-CALZADO-01', 'DEMO-ESI-CALZADO-02', 'DEMO-ESI-CALZADO-03']),
                ('company_id', '=', company.id),
            ])
            if demo_mos:
                demo_mos.action_esi_refresh_material_costs()

            message = (
                'DEMO CARGADA CORRECTAMENTE\n\n'
                'Productos terminados: 3\n'
                'Listas de materiales: 3\n'
                'Materias primas: %s\n'
                'Órdenes de fabricación: %s\n'
                'Destajos: %s\n\n'
                'Valoración: AVCO + Automática\n'
                'Cuenta MP: 153000\n'
                'Producción en Proceso: 154000\n'
                'Producto Terminado: 155000\n'
                'Analítica: una cuenta por producto terminado.'
            ) % (len(defs), mo_count, destajo_count)
            self.result = message

            return {
                'type': 'ir.actions.act_window',
                'name': _('ESI Demo Calzados - Cargada'),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': dict(self.env.context),
            }
        except Exception as exc:
            _logger.exception('Error cargando ESI Calzados Demo')
            # La carga se ejecuta desde un botón y no durante instalación. Así
            # Odoo devuelve el error en pantalla y el módulo permanece instalado.
            raise UserError(_(
                'No se pudo completar la carga de la demo.\n\nDetalle técnico: %s\n\n'
                'Envíeme este mensaje y lo corregimos sin reinstalar el módulo.'
            ) % str(exc))

    def action_open_demo_mos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de fabricación - Demo ESI Calzados'),
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [
                ('origin', 'in', ['DEMO-ESI-CALZADO-01', 'DEMO-ESI-CALZADO-02', 'DEMO-ESI-CALZADO-03']),
                ('company_id', '=', self.company_id.id),
            ],
        }
