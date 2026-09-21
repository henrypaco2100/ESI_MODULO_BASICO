# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID, fields


def _ref(env, xmlid):
    try:
        return env.ref(xmlid)
    except Exception:
        return False


def _get_or_create_account(env, company, code, name, type_xmlid, reconcile=False):
    Account = env['account.account'].sudo().with_context(force_company=company.id)
    account = Account.search([('company_id', '=', company.id), ('code', '=', code)], limit=1)
    if account:
        return account
    user_type = _ref(env, type_xmlid)
    vals = {
        'code': code,
        'name': name,
        'company_id': company.id,
        'reconcile': reconcile,
    }
    if user_type:
        vals['user_type_id'] = user_type.id
    return Account.create(vals)


def _get_or_create_journal(env, company):
    Journal = env['account.journal'].sudo().with_context(force_company=company.id)
    journal = Journal.search([('company_id', '=', company.id), ('code', '=', 'ESIPR')], limit=1)
    if not journal:
        journal = Journal.create({
            'name': 'Valoración Producción ESI',
            'code': 'ESIPR',
            'type': 'general',
            'company_id': company.id,
        })
    return journal


def _get_or_create_category(env, company, name, valuation_account, stock_input, stock_output,
                            price_difference, journal, income_account=None, expense_account=None):
    Category = env['product.category'].sudo().with_context(force_company=company.id)
    category = Category.search([('name', '=', name)], limit=1)
    if not category:
        category = Category.create({'name': name})
    vals = {
        'property_cost_method': 'average',
        'property_valuation': 'real_time',
    }
    fld = category._fields
    if 'property_stock_valuation_account_id' in fld:
        vals['property_stock_valuation_account_id'] = valuation_account.id
    if 'property_stock_account_input_categ_id' in fld:
        vals['property_stock_account_input_categ_id'] = stock_input.id
    if 'property_stock_account_output_categ_id' in fld:
        vals['property_stock_account_output_categ_id'] = stock_output.id
    if 'property_account_creditor_price_difference_categ' in fld:
        vals['property_account_creditor_price_difference_categ'] = price_difference.id
    if 'property_stock_journal' in fld:
        vals['property_stock_journal'] = journal.id
    if income_account and 'property_account_income_categ_id' in fld:
        vals['property_account_income_categ_id'] = income_account.id
    if expense_account and 'property_account_expense_categ_id' in fld:
        vals['property_account_expense_categ_id'] = expense_account.id
    category.write(vals)
    return category


def _get_or_create_uom(env, category_name, uom_name, rounding=0.01):
    UomCategory = env['uom.category'].sudo()
    Uom = env['uom.uom'].sudo()
    category = UomCategory.search([('name', '=', category_name)], limit=1)
    if not category:
        category = UomCategory.create({'name': category_name})
    uom = Uom.search([('name', '=', uom_name), ('category_id', '=', category.id)], limit=1)
    if not uom:
        uom = Uom.create({
            'name': uom_name,
            'category_id': category.id,
            'uom_type': 'reference',
            'factor': 1.0,
            'rounding': rounding,
        })
    return uom


def _get_or_create_attribute(env, name, values):
    Attribute = env['product.attribute'].sudo()
    Value = env['product.attribute.value'].sudo()
    attr = Attribute.search([('name', '=', name)], limit=1)
    if not attr:
        vals = {'name': name}
        if 'create_variant' in Attribute._fields:
            vals['create_variant'] = 'always'
        attr = Attribute.create(vals)
    result = {}
    for value_name in values:
        val = Value.search([('attribute_id', '=', attr.id), ('name', '=', value_name)], limit=1)
        if not val:
            val = Value.create({'attribute_id': attr.id, 'name': value_name})
        result[value_name] = val
    return attr, result


def _ensure_template_attribute_line(env, tmpl, attr, values):
    Line = env['product.template.attribute.line'].sudo()
    line = Line.search([('product_tmpl_id', '=', tmpl.id), ('attribute_id', '=', attr.id)], limit=1)
    vals = {'value_ids': [(6, 0, [v.id for v in values])]}
    if line:
        line.write(vals)
    else:
        vals.update({'product_tmpl_id': tmpl.id, 'attribute_id': attr.id})
        line = Line.create(vals)
    return line


def _get_or_create_product_template(env, company, name, category, uom, list_price, default_code,
                                    talla_attr=None, talla_values=None, color_attr=None, color_values=None,
                                    analytic=None):
    Tmpl = env['product.template'].sudo().with_context(force_company=company.id)
    tmpl = Tmpl.search([('name', '=', name), ('company_id', 'in', [False, company.id])], limit=1)
    vals = {
        'name': name,
        'type': 'product',
        'categ_id': category.id,
        'uom_id': uom.id,
        'uom_po_id': uom.id,
        'list_price': list_price,
        'default_code': default_code,
        'company_id': company.id,
    }
    if analytic:
        vals['esi_production_analytic_account_id'] = analytic.id
    if tmpl:
        tmpl.write(vals)
    else:
        tmpl = Tmpl.create(vals)
    if talla_attr and talla_values:
        _ensure_template_attribute_line(env, tmpl, talla_attr, talla_values)
    if color_attr and color_values:
        _ensure_template_attribute_line(env, tmpl, color_attr, color_values)
    # Fuerza regeneración de variantes si el método está disponible.
    if hasattr(tmpl, '_create_variant_ids'):
        tmpl._create_variant_ids()
    return tmpl


def _get_or_create_raw_product(env, company, name, category, uom, cost, code, vendor=None):
    Tmpl = env['product.template'].sudo().with_context(force_company=company.id)
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
    if vendor:
        SupplierInfo = env['product.supplierinfo'].sudo()
        seller = SupplierInfo.search([
            ('name', '=', vendor.id), ('product_tmpl_id', '=', tmpl.id)
        ], limit=1)
        svals = {
            'name': vendor.id,
            'product_tmpl_id': tmpl.id,
            'min_qty': 0.0,
            'price': cost,
        }
        if seller:
            seller.write(svals)
        else:
            SupplierInfo.create(svals)
    return product


def _create_or_update_bom(env, company, tmpl, code, lines):
    Bom = env['mrp.bom'].sudo().with_context(force_company=company.id)
    BomLine = env['mrp.bom.line'].sudo().with_context(force_company=company.id)
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
        bom.write(vals)
        bom.bom_line_ids.unlink()
    else:
        bom = Bom.create(vals)
    for item in lines:
        product, qty, group = item[:3]
        lvals = {
            'bom_id': bom.id,
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': product.uom_id.id,
            'esi_material_group': group,
        }
        # Cuarto elemento opcional: recordset de product.template.attribute.value.
        if len(item) > 3 and item[3]:
            lvals['bom_product_template_attribute_value_ids'] = [(6, 0, item[3].ids)]
        BomLine.create(lvals)
    return bom


def _get_ptav(tmpl, attribute, value_name):
    lines = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == attribute)
    if not lines:
        return tmpl.env['product.template.attribute.value']
    return lines.product_template_value_ids.filtered(lambda v: v.name == value_name)


def _get_or_create_analytic(env, company, name, code):
    Analytic = env['account.analytic.account'].sudo().with_context(force_company=company.id)
    domain = [('name', '=', name), ('company_id', 'in', [False, company.id])]
    account = Analytic.search(domain, limit=1)
    vals = {'name': name, 'company_id': company.id}
    if 'code' in Analytic._fields:
        vals['code'] = code
    if account:
        account.write(vals)
    else:
        account = Analytic.create(vals)
    return account


def _get_or_create_partner(env, name, supplier=False):
    Partner = env['res.partner'].sudo()
    partner = Partner.search([('name', '=', name)], limit=1)
    vals = {'name': name, 'company_type': 'person'}
    if supplier and 'supplier_rank' in Partner._fields:
        vals['supplier_rank'] = max(partner.supplier_rank if partner else 0, 1)
    if partner:
        partner.write(vals)
    else:
        partner = Partner.create(vals)
    return partner


def _get_or_create_activity(env, company, code, name, price, sequence):
    Model = env['esi.calzado.destajo.actividad'].sudo()
    rec = Model.search([('company_id', '=', company.id), ('code', '=', code)], limit=1)
    vals = {
        'company_id': company.id,
        'code': code,
        'name': name,
        'default_unit_price': price,
        'sequence': sequence,
    }
    if rec:
        rec.write(vals)
    else:
        rec = Model.create(vals)
    return rec


def _create_demo_mo(env, company, product, bom, qty, analytic, origin):
    Production = env['mrp.production'].sudo().with_context(default_company_id=company.id, force_company=company.id)
    existing = Production.search([('origin', '=', origin), ('company_id', '=', company.id)], limit=1)
    if existing:
        return existing
    vals = {
        'product_id': product.id,
        'product_qty': qty,
        'product_uom_id': product.uom_id.id,
        'bom_id': bom.id,
        'company_id': company.id,
        'origin': origin,
        'esi_analytic_account_id': analytic.id,
    }
    mo = Production.create(vals)
    mo.action_confirm()
    return mo


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.user.company_id

    # ------------------------------------------------------------------
    # 1) CUENTAS Y VALORACIÓN AUTOMÁTICA
    # ------------------------------------------------------------------
    raw_account = _get_or_create_account(env, company, '153000', 'Materias primas', 'account.data_account_type_current_assets')
    wip_account = _get_or_create_account(env, company, '154000', 'Producción en Proceso', 'account.data_account_type_current_assets')
    finished_account = _get_or_create_account(env, company, '155000', 'Productos terminados', 'account.data_account_type_current_assets')
    stock_input = _get_or_create_account(env, company, '214001', 'Mercaderías recibidas pendientes de facturar', 'account.data_account_type_current_liabilities', True)
    stock_output = _get_or_create_account(env, company, '158001', 'Mercaderías entregadas pendientes de facturar', 'account.data_account_type_current_assets', True)
    price_diff = _get_or_create_account(env, company, '525001', 'Diferencia de precio de compra', 'account.data_account_type_expenses')
    piecework_payable = _get_or_create_account(env, company, '215500', 'Destajos por pagar - Producción', 'account.data_account_type_current_liabilities', True)
    income = _get_or_create_account(env, company, '411010', 'Ventas de productos terminados', 'account.data_account_type_revenue')
    expense = _get_or_create_account(env, company, '611010', 'Costo de productos terminados vendidos', 'account.data_account_type_expenses')
    journal = _get_or_create_journal(env, company)

    company.sudo().write({
        'esi_wip_account_id': wip_account.id,
        'esi_piecework_payable_account_id': piecework_payable.id,
        'esi_production_journal_id': journal.id,
    })

    production_location = _ref(env, 'stock.stock_location_production')
    if not production_location:
        production_location = env['stock.location'].sudo().search([('usage', '=', 'production')], limit=1)
    if production_location:
        pvals = {}
        if 'valuation_in_account_id' in production_location._fields:
            pvals['valuation_in_account_id'] = wip_account.id
        if 'valuation_out_account_id' in production_location._fields:
            pvals['valuation_out_account_id'] = wip_account.id
        if pvals:
            production_location.sudo().write(pvals)

    raw_cat = _get_or_create_category(
        env, company, 'ESI DEMO - Materias Primas AVCO', raw_account,
        stock_input, stock_output, price_diff, journal, income, expense
    )
    finished_cat = _get_or_create_category(
        env, company, 'ESI DEMO - Producto Terminado AVCO', finished_account,
        stock_input, stock_output, price_diff, journal, income, expense
    )

    # ------------------------------------------------------------------
    # 2) UDM, VARIANTES Y CUENTAS ANALÍTICAS
    # ------------------------------------------------------------------
    pair_uom = _get_or_create_uom(env, 'Calzado ESI', 'Par', 1.0)
    ft2_uom = _get_or_create_uom(env, 'Área ESI', 'ft²', 0.01)
    unit_uom = _ref(env, 'uom.product_uom_unit') or env['uom.uom'].sudo().search([], limit=1)
    meter_uom = _ref(env, 'uom.product_uom_meter') or unit_uom
    gram_uom = _ref(env, 'uom.product_uom_gram') or unit_uom

    talla_attr, talla = _get_or_create_attribute(env, 'Talla', ['39', '40', '41', '42', '43'])
    color_attr, color = _get_or_create_attribute(env, 'Color', ['Negro', 'Café', 'Beige'])

    aa_lona = _get_or_create_analytic(env, company, 'Producción - Bota Lona', 'CALZ-LONA')
    aa_cuero = _get_or_create_analytic(env, company, 'Producción - Bota Puro Cuero', 'CALZ-CUERO')
    aa_tenis = _get_or_create_analytic(env, company, 'Producción - Tenis Táctico', 'CALZ-TENIS')

    bota_lona = _get_or_create_product_template(
        env, company, 'Bota Lona ESI Demo', finished_cat, pair_uom, 280.0, 'PT-BLONA',
        talla_attr, [talla['40'], talla['41'], talla['42']],
        color_attr, [color['Negro'], color['Café']], aa_lona
    )
    bota_cuero = _get_or_create_product_template(
        env, company, 'Bota Puro Cuero ESI Demo', finished_cat, pair_uom, 420.0, 'PT-BCUERO',
        talla_attr, [talla['40'], talla['41'], talla['42'], talla['43']],
        color_attr, [color['Negro'], color['Café']], aa_cuero
    )
    tenis = _get_or_create_product_template(
        env, company, 'Tenis Táctico ESI Demo', finished_cat, pair_uom, 320.0, 'PT-TTACT',
        talla_attr, [talla['39'], talla['40'], talla['41'], talla['42']],
        color_attr, [color['Negro'], color['Beige']], aa_tenis
    )

    # ------------------------------------------------------------------
    # 3) MATERIALES Y PROVEEDOR
    # ------------------------------------------------------------------
    vendor = _get_or_create_partner(env, 'Proveedor Materiales Calzado ESI Demo', supplier=True)
    mats = {}
    defs = [
        ('cuero_hunting', 'Cuero Hunting', ft2_uom, 14.00, 'MP-CUERO-H'),
        ('lona', 'Lona', meter_uom, 44.00, 'MP-LONA'),
        ('lobo_marino', 'Lobo Marino', meter_uom, 35.00, 'MP-LOBO'),
        ('fibra', 'Fibra espuma', meter_uom, 15.00, 'MP-FIBRA'),
        ('gamuzon', 'Gamuzón / Reciclado', ft2_uom, 9.00, 'MP-GAMUZ'),
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
    for key, name, uom, cost, code in defs:
        mats[key] = _get_or_create_raw_product(env, company, name, raw_cat, uom, cost, code, vendor)

    # ------------------------------------------------------------------
    # 4) LISTAS DE MATERIALES. Se demuestra aplicación por Talla.
    # ------------------------------------------------------------------
    bl40 = _get_ptav(bota_lona, talla_attr, '40')
    bl41 = _get_ptav(bota_lona, talla_attr, '41')
    bl42 = _get_ptav(bota_lona, talla_attr, '42')
    bc40 = _get_ptav(bota_cuero, talla_attr, '40')
    bc41 = _get_ptav(bota_cuero, talla_attr, '41')
    bc42 = _get_ptav(bota_cuero, talla_attr, '42')
    bc43 = _get_ptav(bota_cuero, talla_attr, '43')

    bom_lona = _create_or_update_bom(env, company, bota_lona, 'BOM-ESI-BLONA', [
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

    bom_cuero = _create_or_update_bom(env, company, bota_cuero, 'BOM-ESI-BCUERO', [
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

    bom_tenis = _create_or_update_bom(env, company, tenis, 'BOM-ESI-TTACT', [
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

    # ------------------------------------------------------------------
    # 5) DESTAJOS DE EJEMPLO Y 3 ÓRDENES DE FABRICACIÓN
    # ------------------------------------------------------------------
    corte = _get_or_create_activity(env, company, 'CORTE', 'Corte', 1.20, 10)
    aparado = _get_or_create_activity(env, company, 'APARADO', 'Aparado', 2.00, 20)
    armado = _get_or_create_activity(env, company, 'ARMADO', 'Armado', 1.50, 30)
    acabado = _get_or_create_activity(env, company, 'ACABADO', 'Acabado', 0.90, 40)

    emilio = _get_or_create_partner(env, 'Emilio Barrera')
    edith = _get_or_create_partner(env, 'Edith Poma')
    carlos = _get_or_create_partner(env, 'Carlos Mamani')

    # Elige una variante concreta de cada plantilla para demostrar Talla/Color.
    prod_lona = bota_lona.product_variant_ids.filtered(
        lambda p: '42' in p.product_template_attribute_value_ids.mapped('name') and 'Negro' in p.product_template_attribute_value_ids.mapped('name')
    )[:1] or bota_lona.product_variant_ids[:1]
    prod_cuero = bota_cuero.product_variant_ids.filtered(
        lambda p: '41' in p.product_template_attribute_value_ids.mapped('name') and 'Café' in p.product_template_attribute_value_ids.mapped('name')
    )[:1] or bota_cuero.product_variant_ids[:1]
    prod_tenis = tenis.product_variant_ids.filtered(
        lambda p: '40' in p.product_template_attribute_value_ids.mapped('name') and 'Negro' in p.product_template_attribute_value_ids.mapped('name')
    )[:1] or tenis.product_variant_ids[:1]

    mo1 = _create_demo_mo(env, company, prod_lona, bom_lona, 50.0, aa_lona, 'DEMO-ESI-CALZADO-01')
    mo2 = _create_demo_mo(env, company, prod_cuero, bom_cuero, 40.0, aa_cuero, 'DEMO-ESI-CALZADO-02')
    mo3 = _create_demo_mo(env, company, prod_tenis, bom_tenis, 60.0, aa_tenis, 'DEMO-ESI-CALZADO-03')

    Destajo = env['esi.calzado.destajo'].sudo()
    demo_destajos = [
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
    for mo, worker, activity, qty, rate, description in demo_destajos:
        exists = Destajo.search([
            ('production_id', '=', mo.id), ('partner_id', '=', worker.id),
            ('activity_id', '=', activity.id), ('description', '=', description)
        ], limit=1)
        if not exists:
            Destajo.create({
                'production_id': mo.id,
                'partner_id': worker.id,
                'activity_id': activity.id,
                'description': description,
                'quantity': qty,
                'uom_id': pair_uom.id,
                'unit_price': rate,
                'date': fields.Date.context_today(env.user),
                # Quedan en borrador deliberadamente: el usuario decide cuándo contabilizar.
                'state': 'draft',
            })
