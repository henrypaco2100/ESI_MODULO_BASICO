# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api, fields


MODULE = 'esi_demo_farmacia_v13'


def _bind_xmlid(env, name, record):
    """Vincula el registro al módulo para que sea fácil identificar el dato demo."""
    if not record:
        return record
    imd = env['ir.model.data'].sudo()
    existing = imd.search([
        ('module', '=', MODULE),
        ('name', '=', name),
    ], limit=1)
    vals = {
        'module': MODULE,
        'name': name,
        'model': record._name,
        'res_id': record.id,
        'noupdate': True,
    }
    if existing:
        existing.write(vals)
    else:
        imd.create(vals)
    return record


def _ref(env, xmlid):
    return env.ref(xmlid, raise_if_not_found=False)


def _get_or_create(env, model_name, xmlid_name, domain, vals):
    record = _ref(env, '%s.%s' % (MODULE, xmlid_name))
    if record and record._name == model_name and record.exists():
        record.sudo().write(vals)
        return record
    model = env[model_name].sudo()
    record = model.search(domain, limit=1)
    if record:
        record.write(vals)
    else:
        record = model.create(vals)
    return _bind_xmlid(env, xmlid_name, record)


def _account_type(env, xmlid):
    record = _ref(env, xmlid)
    if not record:
        raise ValueError('No se encontró el tipo de cuenta requerido: %s' % xmlid)
    return record


def _account(env, company, xmlid_name, code, name, type_xmlid, reconcile=False):
    vals = {
        'code': code,
        'name': name,
        'user_type_id': _account_type(env, type_xmlid).id,
        'company_id': company.id,
        'reconcile': reconcile,
    }
    return _get_or_create(
        env, 'account.account', xmlid_name,
        [('code', '=', code), ('company_id', '=', company.id)], vals)


def _journal(env, company, store, xmlid_name, name, code, journal_type, default_account=None):
    vals = {
        'name': name,
        'code': code,
        'type': journal_type,
        'company_id': company.id,
        'store_id': store.id if store else False,
    }
    if default_account:
        if 'default_debit_account_id' in env['account.journal']._fields:
            vals['default_debit_account_id'] = default_account.id
        if 'default_credit_account_id' in env['account.journal']._fields:
            vals['default_credit_account_id'] = default_account.id
    return _get_or_create(
        env, 'account.journal', xmlid_name,
        [('code', '=', code), ('company_id', '=', company.id)], vals)


def _sequence(env, company, xmlid_name, name, code, prefix):
    vals = {
        'name': name,
        'code': code,
        'prefix': prefix,
        'padding': 4,
        'number_increment': 1,
        'implementation': 'no_gap',
        'company_id': company.id,
    }
    return _get_or_create(
        env, 'ir.sequence', xmlid_name,
        [('code', '=', code), ('company_id', '=', company.id)], vals)


def _financial_report(env, xmlid_name, name, sequence, report_type='sum', parent=None,
                      number=None, sign='1', report_group='hijos', accounts=None,
                      account_report=None, style='0', planilla=None):
    vals = {
        'name': name,
        'sequence': sequence,
        'type': report_type,
        'parent_id': parent.id if parent else False,
        'sd_numero_cuenta': number or False,
        'sign': sign,
        'sd_tipo_reporte': report_group,
        'style_overwrite': style,
        'display_detail': 'detail_flat',
    }
    if accounts is not None:
        vals['account_ids'] = [(6, 0, accounts.ids)]
    if account_report:
        vals['account_report_id'] = account_report.id
    if planilla:
        vals['sd_planilla'] = planilla.id
    record = _get_or_create(
        env, 'account.financial.report', xmlid_name,
        [('name', '=', name), ('sd_numero_cuenta', '=', number or False)], vals)
    return record


def _result_component(env, parent_report, report, operation, xmlid_name):
    vals = {
        'sd_report_bi_financial_id': parent_report.id,
        'sd_report_id': report.id,
        'sd_operacion_report': operation,
        'name': report.name,
    }
    return _get_or_create(
        env, 'account.financial.report.line', xmlid_name,
        [('sd_report_bi_financial_id', '=', parent_report.id), ('sd_report_id', '=', report.id)], vals)


def _product_category(env, company, xmlid_name, name, valuation_account, input_account,
                      output_account, income_account, expense_account, stock_journal):
    vals = {'name': name}
    categ = _get_or_create(env, 'product.category', xmlid_name, [('name', '=', name)], vals)
    company_vals = {
        'property_cost_method': 'average',
        'property_valuation': 'real_time',
        'property_stock_valuation_account_id': valuation_account.id,
        'property_stock_account_input_categ_id': input_account.id,
        'property_stock_account_output_categ_id': output_account.id,
        'property_account_income_categ_id': income_account.id,
        'property_account_expense_categ_id': expense_account.id,
        'property_stock_journal': stock_journal.id,
    }
    categ.with_context(force_company=company.id).sudo().write(company_vals)
    return categ


def _product(env, xmlid_name, default_code, name, category, cost, sale_price):
    ProductTemplate = env['product.template'].sudo()
    vals = {
        'name': name,
        'default_code': default_code,
        'type': 'product',
        'categ_id': category.id,
        'standard_price': cost,
        'list_price': sale_price,
        'sale_ok': True,
        'purchase_ok': True,
    }
    if 'invoice_policy' in ProductTemplate._fields:
        vals['invoice_policy'] = 'order'
    if 'purchase_method' in ProductTemplate._fields:
        vals['purchase_method'] = 'purchase'
    unit = _ref(env, 'uom.product_uom_unit')
    if unit:
        vals['uom_id'] = unit.id
        vals['uom_po_id'] = unit.id
    template = _get_or_create(
        env, 'product.template', xmlid_name,
        [('default_code', '=', default_code)], vals)
    return template.product_variant_id


def _partner(env, company, xmlid_name, name, receivable, payable, pricelist, customer=False, supplier=False):
    Partner = env['res.partner'].sudo()
    vals = {
        'name': name,
        'company_type': 'company',
        'company_id': company.id,
    }
    if 'customer_rank' in Partner._fields:
        vals['customer_rank'] = 1 if customer else 0
    if 'supplier_rank' in Partner._fields:
        vals['supplier_rank'] = 1 if supplier else 0
    partner = _get_or_create(env, 'res.partner', xmlid_name, [('name', '=', name), ('company_id', '=', company.id)], vals)
    prop_vals = {
        'property_account_receivable_id': receivable.id,
        'property_account_payable_id': payable.id,
    }
    if pricelist and 'property_product_pricelist' in Partner._fields:
        prop_vals['property_product_pricelist'] = pricelist.id
    partner.with_context(force_company=company.id).write(prop_vals)
    return partner


def _warehouse(env, company, store, xmlid_name, name, code, use_existing=False):
    record = _ref(env, '%s.%s' % (MODULE, xmlid_name))
    if record and record.exists():
        record.write({'name': name, 'code': code, 'store_id': store.id})
        return record
    Warehouse = env['stock.warehouse'].sudo()
    record = Warehouse.search([('company_id', '=', company.id), ('name', '=', name)], limit=1)
    if not record and use_existing:
        unassigned = Warehouse.search([('company_id', '=', company.id), ('store_id', '=', False)], limit=1)
        if unassigned:
            record = unassigned
    vals = {'name': name, 'code': code, 'company_id': company.id, 'store_id': store.id}
    if record:
        # El código puede estar usado por el almacén que estamos reutilizando; el propio registro puede conservarlo.
        other = Warehouse.search([('company_id', '=', company.id), ('code', '=', code), ('id', '!=', record.id)], limit=1)
        if other:
            code = ('CE' if name == 'Central' else 'MO') + str(record.id)
            vals['code'] = code[:5]
        record.write(vals)
    else:
        other = Warehouse.search([('company_id', '=', company.id), ('code', '=', code)], limit=1)
        if other:
            code = (code[:3] + str(len(Warehouse.search([('company_id', '=', company.id)])) + 1))[:5]
            vals['code'] = code
        record = Warehouse.create(vals)
    return _bind_xmlid(env, xmlid_name, record)


def _sale_type(env, company, store, warehouse, sale_journal, sequence,
               xmlid_name, name, order, validate_delivery):
    vals = {
        'name': name,
        'sequence': order,
        'company_id': company.id,
        'store_id': store.id,
        'st_almacen': warehouse.id,
        'st_secuencia_quotation': sequence.id,
        'sales_journal': sale_journal.id,
        'validation_picking': validate_delivery,
        'validate_invoice': True,
        'allow_payment_from_sale': True,
        'active': True,
    }
    return _get_or_create(env, 'automated.sale', xmlid_name,
                          [('name', '=', name), ('company_id', '=', company.id)], vals)


def _purchase_type(env, company, store, warehouse, purchase_journal, sequence,
                   xmlid_name, name, order, validate_receipt):
    vals = {
        'name': name,
        'sequence': order,
        'company_id': company.id,
        'store_id': store.id,
        'st_almacen': warehouse.id,
        'st_entregar_a': warehouse.in_type_id.id,
        'st_secuencia_quotation': sequence.id,
        'purchase_journal': purchase_journal.id,
        'validation_picking': validate_receipt,
        'validate_invoice': True,
        'allow_payment_from_purchase': True,
        'active': True,
    }
    return _get_or_create(env, 'automated.purchase', xmlid_name,
                          [('name', '=', name), ('company_id', '=', company.id)], vals)


def _pos_payment_method(env, company, xmlid_name, name, receivable_account, cash_journal):
    vals = {
        'name': name,
        'receivable_account_id': receivable_account.id,
        'is_cash_count': True,
        'cash_journal_id': cash_journal.id,
        'company_id': company.id,
    }
    return _get_or_create(env, 'pos.payment.method', xmlid_name,
                          [('name', '=', name), ('company_id', '=', company.id)], vals)


def _pos_config(env, company, warehouse, sale_journal, pricelist, payment_method, xmlid_name, name):
    PosConfig = env['pos.config'].sudo()
    vals = {'name': name}
    if 'company_id' in PosConfig._fields:
        vals['company_id'] = company.id
    if 'picking_type_id' in PosConfig._fields:
        pos_type = getattr(warehouse, 'pos_type_id', False) or warehouse.out_type_id
        vals['picking_type_id'] = pos_type.id
    if 'journal_id' in PosConfig._fields:
        vals['journal_id'] = sale_journal.id
    if 'invoice_journal_id' in PosConfig._fields:
        vals['invoice_journal_id'] = sale_journal.id
    if 'pricelist_id' in PosConfig._fields:
        vals['pricelist_id'] = pricelist.id
    if 'available_pricelist_ids' in PosConfig._fields:
        vals['available_pricelist_ids'] = [(6, 0, [pricelist.id])]
    if 'payment_method_ids' in PosConfig._fields:
        vals['payment_method_ids'] = [(6, 0, [payment_method.id])]
    return _get_or_create(env, 'pos.config', xmlid_name, [('name', '=', name)], vals)


def _purchase_order(env, xmlid_name, partner, purchase_type, lines, company):
    PurchaseOrder = env['purchase.order'].sudo()
    existing = _ref(env, '%s.%s' % (MODULE, xmlid_name))
    if existing and existing.exists():
        return existing
    vals = {
        'partner_id': partner.id,
        'company_id': company.id,
        'work_process_order_id': purchase_type.id,
        'date_order': fields.Datetime.now(),
        'order_line': [],
    }
    for product, qty, price in lines:
        vals['order_line'].append((0, 0, {
            'product_id': product.id,
            'name': product.display_name,
            'product_qty': qty,
            'product_uom': product.uom_po_id.id,
            'price_unit': price,
            'date_planned': fields.Datetime.now(),
        }))
    order = PurchaseOrder.create(vals)
    _bind_xmlid(env, xmlid_name, order)
    order.button_confirm()
    return order


def _sale_order(env, xmlid_name, partner, sale_type, pricelist, lines, company):
    SaleOrder = env['sale.order'].sudo()
    existing = _ref(env, '%s.%s' % (MODULE, xmlid_name))
    if existing and existing.exists():
        return existing
    vals = {
        'partner_id': partner.id,
        'company_id': company.id,
        'pricelist_id': pricelist.id,
        'work_process_order_id': sale_type.id,
        'date_order': fields.Datetime.now(),
        'order_line': [],
    }
    for product, qty, price in lines:
        vals['order_line'].append((0, 0, {
            'product_id': product.id,
            'name': product.display_name,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': price,
        }))
    order = SaleOrder.create(vals)
    _bind_xmlid(env, xmlid_name, order)
    order.action_confirm()
    return order


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref('base.main_company')

    # ------------------------------------------------------------------
    # 1) Moneda / empresa y plan contable básico Bolivia
    # ------------------------------------------------------------------
    bob = _ref(env, 'base.BOB')
    if bob and not bob.active:
        bob.sudo().write({'active': True})
    # En una base nueva de demo usamos Bolivianos. Si ya existen apuntes, no alteramos la moneda.
    if bob and not env['account.move.line'].sudo().search_count([('company_id', '=', company.id)]):
        company.sudo().write({'currency_id': bob.id})
    bolivia = _ref(env, 'base.bo')
    if bolivia and not company.country_id:
        company.sudo().write({'country_id': bolivia.id})

    acc = {}
    account_defs = [
        ('cash_central', '11101', 'Caja Moneda Nacional - Central', 'account.data_account_type_liquidity', False),
        ('bank_central', '11102', 'Banco - Central', 'account.data_account_type_liquidity', False),
        ('cash_montero', '11103', 'Caja Moneda Nacional - Montero', 'account.data_account_type_liquidity', False),
        ('bank_montero', '11104', 'Banco - Montero', 'account.data_account_type_liquidity', False),
        ('receivable', '11201', 'Cuentas por Cobrar Clientes', 'account.data_account_type_receivable', True),
        ('pos_receivable_central', '11202', 'Cuenta Puente POS - Central', 'account.data_account_type_receivable', True),
        ('pos_receivable_montero', '11203', 'Cuenta Puente POS - Montero', 'account.data_account_type_receivable', True),
        ('inventory', '11301', 'Inventario de Mercaderías Farmacia', 'account.data_account_type_current_assets', False),
        ('iva_credit', '11401', 'Crédito Fiscal IVA', 'account.data_account_type_current_assets', False),
        ('stock_input', '11501', 'Mercaderías Recibidas por Facturar', 'account.data_account_type_current_assets', True),
        ('stock_output', '11502', 'Mercaderías Entregadas por Facturar', 'account.data_account_type_current_assets', True),
        ('fixed_assets', '12101', 'Muebles y Enseres', 'account.data_account_type_fixed_assets', False),
        ('depreciation', '12901', 'Depreciación Acumulada', 'account.data_account_type_fixed_assets', False),
        ('payable', '21101', 'Cuentas por Pagar Proveedores', 'account.data_account_type_payable', True),
        ('iva_debit', '21201', 'Débito Fiscal IVA', 'account.data_account_type_current_liabilities', False),
        ('wages_payable', '21301', 'Sueldos por Pagar', 'account.data_account_type_current_liabilities', True),
        ('capital', '31101', 'Capital Social', 'account.data_account_type_equity', False),
        ('retained', '32101', 'Resultados Acumulados', 'account.data_account_type_equity', False),
        ('sales', '41101', 'Ventas de Mercaderías', 'account.data_account_type_revenue', False),
        ('other_income', '42101', 'Otros Ingresos', 'account.data_account_type_other_income', False),
        ('cogs', '51101', 'Costo de Ventas', 'account.data_account_type_direct_costs', False),
        ('wages', '61101', 'Sueldos y Salarios', 'account.data_account_type_expenses', False),
        ('rent', '61201', 'Alquileres', 'account.data_account_type_expenses', False),
        ('utilities', '61301', 'Servicios Básicos', 'account.data_account_type_expenses', False),
        ('admin_exp', '61401', 'Gastos Administrativos', 'account.data_account_type_expenses', False),
        ('financial_exp', '61501', 'Gastos Financieros', 'account.data_account_type_expenses', False),
    ]
    # Algunas instalaciones de Odoo no incluyen el XML ID other_income/direct_costs.
    fallback_types = {
        'account.data_account_type_other_income': 'account.data_account_type_revenue',
        'account.data_account_type_direct_costs': 'account.data_account_type_expenses',
    }
    for key, code, name, type_xmlid, reconcile in account_defs:
        if not _ref(env, type_xmlid) and type_xmlid in fallback_types:
            type_xmlid = fallback_types[type_xmlid]
        acc[key] = _account(env, company, 'account_%s' % key, code, name, type_xmlid, reconcile)

    # ------------------------------------------------------------------
    # 2) Sucursales y almacenes
    # ------------------------------------------------------------------
    store_central = _get_or_create(
        env, 'res.store', 'store_central',
        [('name', '=', 'Central'), ('company_id', '=', company.id)],
        {'name': 'Central', 'company_id': company.id})
    store_montero = _get_or_create(
        env, 'res.store', 'store_montero',
        [('name', '=', 'Sucursal Montero'), ('company_id', '=', company.id)],
        {'name': 'Sucursal Montero', 'company_id': company.id})

    warehouse_central = _warehouse(env, company, store_central, 'warehouse_central', 'Central', 'CEN', use_existing=True)
    warehouse_montero = _warehouse(env, company, store_montero, 'warehouse_montero', 'Sucursal Montero', 'MON', use_existing=False)

    admin = _ref(env, 'base.user_admin')
    if admin and 'store_ids' in admin._fields:
        admin.sudo().write({
            'store_ids': [(6, 0, [store_central.id, store_montero.id])],
            'store_id': store_central.id,
        })

    # ------------------------------------------------------------------
    # 3) Diarios y secuencias por sucursal
    # ------------------------------------------------------------------
    stock_journal = _journal(env, company, False, 'journal_stock_valuation', 'Valoración Inventario ESI', 'STK', 'general')

    sale_journal_central = _journal(env, company, store_central, 'journal_sale_central', 'Ventas Central', 'CENV', 'sale')
    purchase_journal_central = _journal(env, company, store_central, 'journal_purchase_central', 'Compras Central', 'CENC', 'purchase')
    bank_journal_central = _journal(env, company, store_central, 'journal_bank_central', 'Banco Central', 'CENB', 'bank', acc['bank_central'])
    cash_journal_central = _journal(env, company, store_central, 'journal_cash_central', 'Caja Central', 'CECA', 'cash', acc['cash_central'])

    sale_journal_montero = _journal(env, company, store_montero, 'journal_sale_montero', 'Ventas Montero', 'MONV', 'sale')
    purchase_journal_montero = _journal(env, company, store_montero, 'journal_purchase_montero', 'Compras Montero', 'MONC', 'purchase')
    bank_journal_montero = _journal(env, company, store_montero, 'journal_bank_montero', 'Banco Montero', 'MONB', 'bank', acc['bank_montero'])
    cash_journal_montero = _journal(env, company, store_montero, 'journal_cash_montero', 'Caja Montero', 'MOCA', 'cash', acc['cash_montero'])

    seq_sale_central = _sequence(env, company, 'seq_sale_central', 'Venta Central ESI', 'esi.demo.sale.central', 'CEN-V-')
    seq_sale_montero = _sequence(env, company, 'seq_sale_montero', 'Venta Montero ESI', 'esi.demo.sale.montero', 'MON-V-')
    seq_purchase_central = _sequence(env, company, 'seq_purchase_central', 'Compra Central ESI', 'esi.demo.purchase.central', 'CEN-C-')
    seq_purchase_montero = _sequence(env, company, 'seq_purchase_montero', 'Compra Montero ESI', 'esi.demo.purchase.montero', 'MON-C-')

    # ------------------------------------------------------------------
    # 4) Tipos de venta y compra
    # ------------------------------------------------------------------
    sale_types = {
        'central_immediate': _sale_type(env, company, store_central, warehouse_central, sale_journal_central,
                                        seq_sale_central, 'sale_type_central_immediate',
                                        'Venta Inmediata - Central', 10, True),
        'central_pending': _sale_type(env, company, store_central, warehouse_central, sale_journal_central,
                                      seq_sale_central, 'sale_type_central_pending',
                                      'Venta por Entregar - Central', 20, False),
        'montero_immediate': _sale_type(env, company, store_montero, warehouse_montero, sale_journal_montero,
                                        seq_sale_montero, 'sale_type_montero_immediate',
                                        'Venta Inmediata - Montero', 10, True),
        'montero_pending': _sale_type(env, company, store_montero, warehouse_montero, sale_journal_montero,
                                      seq_sale_montero, 'sale_type_montero_pending',
                                      'Venta por Entregar - Montero', 20, False),
    }
    purchase_types = {
        'central_immediate': _purchase_type(env, company, store_central, warehouse_central, purchase_journal_central,
                                            seq_purchase_central, 'purchase_type_central_immediate',
                                            'Compra Inmediata - Central', 10, True),
        'central_import': _purchase_type(env, company, store_central, warehouse_central, purchase_journal_central,
                                         seq_purchase_central, 'purchase_type_central_import',
                                         'Compra Importación - Central', 20, False),
        'montero_immediate': _purchase_type(env, company, store_montero, warehouse_montero, purchase_journal_montero,
                                            seq_purchase_montero, 'purchase_type_montero_immediate',
                                            'Compra Inmediata - Montero', 10, True),
        'montero_import': _purchase_type(env, company, store_montero, warehouse_montero, purchase_journal_montero,
                                         seq_purchase_montero, 'purchase_type_montero_import',
                                         'Compra Importación - Montero', 20, False),
    }

    # ------------------------------------------------------------------
    # 5) Categorías AVCO + valoración automática y 20 productos
    # ------------------------------------------------------------------
    category_meds = _product_category(env, company, 'category_medicamentos', 'ESI Demo / Medicamentos',
                                      acc['inventory'], acc['stock_input'], acc['stock_output'], acc['sales'], acc['cogs'], stock_journal)
    category_retail = _product_category(env, company, 'category_venta_farmacia', 'ESI Demo / Venta Farmacia',
                                        acc['inventory'], acc['stock_input'], acc['stock_output'], acc['sales'], acc['cogs'], stock_journal)

    product_defs = [
        ('far001', 'FAR001', 'Paracetamol 500 mg x 20', category_meds, 8.00, 13.00),
        ('far002', 'FAR002', 'Ibuprofeno 400 mg x 10', category_meds, 9.50, 15.00),
        ('far003', 'FAR003', 'Amoxicilina 500 mg x 20', category_meds, 24.00, 36.00),
        ('far004', 'FAR004', 'Omeprazol 20 mg x 14', category_meds, 12.00, 19.00),
        ('far005', 'FAR005', 'Loratadina 10 mg x 10', category_meds, 7.00, 12.00),
        ('far006', 'FAR006', 'Diclofenaco 50 mg x 20', category_meds, 10.00, 16.00),
        ('far007', 'FAR007', 'Azitromicina 500 mg x 3', category_meds, 20.00, 32.00),
        ('far008', 'FAR008', 'Metformina 850 mg x 30', category_meds, 18.00, 28.00),
        ('far009', 'FAR009', 'Losartán 50 mg x 30', category_meds, 17.00, 27.00),
        ('far010', 'FAR010', 'Vitamina C 1 g x 10', category_meds, 11.00, 18.00),
        ('vta001', 'VTA001', 'Alcohol 70% 1 L', category_retail, 13.00, 21.00),
        ('vta002', 'VTA002', 'Agua Oxigenada 250 ml', category_retail, 5.00, 9.00),
        ('vta003', 'VTA003', 'Algodón Hidrófilo 100 g', category_retail, 6.00, 10.00),
        ('vta004', 'VTA004', 'Gasas Estériles x 10', category_retail, 7.00, 12.00),
        ('vta005', 'VTA005', 'Curitas Adhesivas x 20', category_retail, 5.50, 9.50),
        ('vta006', 'VTA006', 'Termómetro Digital', category_retail, 28.00, 45.00),
        ('vta007', 'VTA007', 'Mascarilla Quirúrgica x 50', category_retail, 24.00, 38.00),
        ('vta008', 'VTA008', 'Guantes de Nitrilo x 100', category_retail, 45.00, 68.00),
        ('vta009', 'VTA009', 'Suero Fisiológico 500 ml', category_retail, 8.00, 13.00),
        ('vta010', 'VTA010', 'Protector Solar SPF 50 120 ml', category_retail, 42.00, 65.00),
    ]
    products = {}
    for key, code, name, categ, cost, sale_price in product_defs:
        products[key] = _product(env, 'product_%s' % key, code, name, categ, cost, sale_price)

    # ------------------------------------------------------------------
    # 6) Tarifa, contactos y cuentas de tercero
    # ------------------------------------------------------------------
    pricelist_vals = {
        'name': 'Tarifa ESI Demo Farmacia',
        'currency_id': company.currency_id.id,
    }
    if 'company_id' in env['product.pricelist']._fields:
        pricelist_vals['company_id'] = company.id
    pricelist = _get_or_create(env, 'product.pricelist', 'pricelist_demo', [('name', '=', 'Tarifa ESI Demo Farmacia')], pricelist_vals)

    vendor_a = _partner(env, company, 'vendor_a', 'Distribuidora Farmacéutica Andina', acc['receivable'], acc['payable'], pricelist, supplier=True)
    vendor_b = _partner(env, company, 'vendor_b', 'Laboratorios Demo Bolivia', acc['receivable'], acc['payable'], pricelist, supplier=True)
    customer_a = _partner(env, company, 'customer_a', 'Cliente Mostrador Central', acc['receivable'], acc['payable'], pricelist, customer=True)
    customer_b = _partner(env, company, 'customer_b', 'Clínica Central Demo', acc['receivable'], acc['payable'], pricelist, customer=True)
    customer_c = _partner(env, company, 'customer_c', 'Cliente Mostrador Montero', acc['receivable'], acc['payable'], pricelist, customer=True)
    customer_d = _partner(env, company, 'customer_d', 'Consultorio Montero Demo', acc['receivable'], acc['payable'], pricelist, customer=True)

    # ------------------------------------------------------------------
    # 7) Dos configuraciones POS asociadas a cada almacén/sucursal
    # ------------------------------------------------------------------
    pos_payment_central = _pos_payment_method(env, company, 'pos_payment_central', 'Efectivo POS Central',
                                              acc['pos_receivable_central'], cash_journal_central)
    pos_payment_montero = _pos_payment_method(env, company, 'pos_payment_montero', 'Efectivo POS Montero',
                                              acc['pos_receivable_montero'], cash_journal_montero)
    _pos_config(env, company, warehouse_central, sale_journal_central, pricelist, pos_payment_central, 'pos_central', 'POS Central')
    _pos_config(env, company, warehouse_montero, sale_journal_montero, pricelist, pos_payment_montero, 'pos_montero', 'POS Montero')

    # ------------------------------------------------------------------
    # 8) Estructura ordenada del Balance General y Estado de Resultados
    # ------------------------------------------------------------------
    balance_action = _ref(env, 'esi_bi_financial_pdf_reports.action_report_balancesheet_v3') or _ref(env, 'esi_bi_financial_pdf_reports.action_report_balancesheet')
    result_action = _ref(env, 'esi_bi_financial_pdf_reports.action_report_estado_resultado_v3') or _ref(env, 'esi_bi_financial_pdf_reports.action_report_estado_resultado')

    bg = _financial_report(env, 'fr_bg', 'BALANCE GENERAL', 10, 'sum', number=False,
                           report_group='balance_general', style='1', planilla=balance_action)
    activo = _financial_report(env, 'fr_activo', 'ACTIVO', 20, 'sum', bg, '1', style='2')
    act_corr = _financial_report(env, 'fr_activo_corriente', 'ACTIVO CORRIENTE', 30, 'sum', activo, '11', style='3')
    _financial_report(env, 'fr_disponible', 'DISPONIBLE', 40, 'accounts', act_corr, '111', accounts=acc['cash_central'] | acc['bank_central'] | acc['cash_montero'] | acc['bank_montero'], style='4')
    _financial_report(env, 'fr_cxc', 'EXIGIBLE / CUENTAS POR COBRAR', 50, 'accounts', act_corr, '112', accounts=acc['receivable'], style='4')
    _financial_report(env, 'fr_inventarios', 'REALIZABLE / INVENTARIOS', 60, 'accounts', act_corr, '113', accounts=acc['inventory'], style='4')
    _financial_report(env, 'fr_otros_activos', 'OTROS ACTIVOS CORRIENTES', 70, 'accounts', act_corr, '114', accounts=acc['iva_credit'] | acc['stock_input'] | acc['stock_output'], style='4')
    act_no_corr = _financial_report(env, 'fr_activo_no_corriente', 'ACTIVO NO CORRIENTE', 80, 'sum', activo, '12', style='3')
    _financial_report(env, 'fr_activos_fijos', 'ACTIVOS FIJOS', 90, 'accounts', act_no_corr, '121', accounts=acc['fixed_assets'], style='4')
    _financial_report(env, 'fr_depreciacion', 'DEPRECIACIÓN ACUMULADA', 100, 'accounts', act_no_corr, '129', accounts=acc['depreciation'], sign='-1', style='4')

    pasivo = _financial_report(env, 'fr_pasivo', 'PASIVO', 110, 'sum', bg, '2', sign='-1', style='2')
    pas_corr = _financial_report(env, 'fr_pasivo_corriente', 'PASIVO CORRIENTE', 120, 'sum', pasivo, '21', sign='-1', style='3')
    _financial_report(env, 'fr_cxp', 'CUENTAS POR PAGAR', 130, 'accounts', pas_corr, '211', accounts=acc['payable'], sign='-1', style='4')
    _financial_report(env, 'fr_impuestos_pagar', 'IMPUESTOS Y OTRAS OBLIGACIONES', 140, 'accounts', pas_corr, '212', accounts=acc['iva_debit'] | acc['wages_payable'], sign='-1', style='4')
    patrimonio = _financial_report(env, 'fr_patrimonio', 'PATRIMONIO', 150, 'sum', bg, '3', sign='-1', style='2')
    _financial_report(env, 'fr_capital', 'CAPITAL SOCIAL', 160, 'accounts', patrimonio, '31', accounts=acc['capital'], sign='-1', style='4')
    _financial_report(env, 'fr_resultados_acum', 'RESULTADOS ACUMULADOS', 170, 'accounts', patrimonio, '32', accounts=acc['retained'], sign='-1', style='4')

    er = _financial_report(env, 'fr_er', 'ESTADO DE RESULTADOS', 1000, 'sum', number=False,
                           report_group='estado_resultado', style='1', planilla=result_action)
    ingresos = _financial_report(env, 'fr_ingresos', 'INGRESOS', 1010, 'sum', er, '4', sign='-1', style='2')
    ventas_line = _financial_report(env, 'fr_ventas', 'VENTAS', 1020, 'accounts', ingresos, '41', accounts=acc['sales'], sign='-1', style='4')
    otros_ingresos_line = _financial_report(env, 'fr_otros_ingresos', 'OTROS INGRESOS', 1030, 'accounts', ingresos, '42', accounts=acc['other_income'], sign='-1', style='4')
    costos = _financial_report(env, 'fr_costos', 'COSTOS', 1040, 'sum', er, '5', style='2')
    cogs_line = _financial_report(env, 'fr_costo_ventas', 'COSTO DE VENTAS', 1050, 'accounts', costos, '51', accounts=acc['cogs'], style='4')
    gastos = _financial_report(env, 'fr_gastos', 'GASTOS OPERATIVOS', 1060, 'sum', er, '6', style='2')
    wages_line = _financial_report(env, 'fr_sueldos', 'SUELDOS Y SALARIOS', 1070, 'accounts', gastos, '61', accounts=acc['wages'], style='4')
    rent_line = _financial_report(env, 'fr_alquileres', 'ALQUILERES', 1080, 'accounts', gastos, '62', accounts=acc['rent'], style='4')
    utilities_line = _financial_report(env, 'fr_servicios', 'SERVICIOS BÁSICOS', 1090, 'accounts', gastos, '63', accounts=acc['utilities'], style='4')
    admin_line = _financial_report(env, 'fr_admin', 'GASTOS ADMINISTRATIVOS', 1100, 'accounts', gastos, '64', accounts=acc['admin_exp'], style='4')
    fin_line = _financial_report(env, 'fr_financieros', 'GASTOS FINANCIEROS', 1110, 'accounts', gastos, '65', accounts=acc['financial_exp'], style='4')
    net_result = _financial_report(env, 'fr_resultado_neto', 'RESULTADO NETO DEL EJERCICIO', 1120, 'result_type', er, False, sign='1', style='2')
    _result_component(env, net_result, ventas_line, '-1', 'fr_result_component_sales')
    _result_component(env, net_result, otros_ingresos_line, '-1', 'fr_result_component_other_income')
    for line, xid in [
        (cogs_line, 'fr_result_component_cogs'),
        (wages_line, 'fr_result_component_wages'),
        (rent_line, 'fr_result_component_rent'),
        (utilities_line, 'fr_result_component_utilities'),
        (admin_line, 'fr_result_component_admin'),
        (fin_line, 'fr_result_component_fin'),
    ]:
        _result_component(env, net_result, line, '-1', xid)
    _financial_report(env, 'fr_resultado_ejercicio_bg', 'RESULTADO DEL EJERCICIO', 180, 'account_report', patrimonio,
                      '33', sign='1', account_report=net_result, style='4')

    # ------------------------------------------------------------------
    # 9) Operaciones de compra: 4 compras (una por tipo/sucursal)
    # ------------------------------------------------------------------
    _purchase_order(env, 'po_central_immediate', vendor_a, purchase_types['central_immediate'], [
        (products['far001'], 80, 8.00), (products['far002'], 60, 9.50),
        (products['far003'], 40, 24.00), (products['vta001'], 50, 13.00),
        (products['vta003'], 50, 6.00),
    ], company)
    _purchase_order(env, 'po_central_import', vendor_b, purchase_types['central_import'], [
        (products['far007'], 40, 20.00), (products['far008'], 50, 18.00),
        (products['vta006'], 20, 28.00), (products['vta010'], 30, 42.00),
    ], company)
    _purchase_order(env, 'po_montero_immediate', vendor_a, purchase_types['montero_immediate'], [
        (products['far004'], 70, 12.00), (products['far005'], 60, 7.00),
        (products['far006'], 50, 10.00), (products['vta002'], 50, 5.00),
        (products['vta004'], 60, 7.00), (products['vta009'], 40, 8.00),
    ], company)
    _purchase_order(env, 'po_montero_import', vendor_b, purchase_types['montero_import'], [
        (products['far009'], 50, 17.00), (products['far010'], 70, 11.00),
        (products['vta007'], 30, 24.00), (products['vta008'], 25, 45.00),
    ], company)

    # ------------------------------------------------------------------
    # 10) Operaciones de venta: 4 ventas (una por tipo/sucursal)
    # ------------------------------------------------------------------
    _sale_order(env, 'so_central_immediate', customer_a, sale_types['central_immediate'], pricelist, [
        (products['far001'], 5, 13.00), (products['far002'], 4, 15.00),
        (products['vta001'], 3, 21.00),
    ], company)
    _sale_order(env, 'so_central_pending', customer_b, sale_types['central_pending'], pricelist, [
        (products['far003'], 3, 36.00), (products['vta003'], 5, 10.00),
        (products['vta006'], 1, 45.00),
    ], company)
    _sale_order(env, 'so_montero_immediate', customer_c, sale_types['montero_immediate'], pricelist, [
        (products['far004'], 5, 19.00), (products['far005'], 4, 12.00),
        (products['vta002'], 4, 9.00), (products['vta004'], 3, 12.00),
    ], company)
    _sale_order(env, 'so_montero_pending', customer_d, sale_types['montero_pending'], pricelist, [
        (products['far006'], 3, 16.00), (products['vta009'], 4, 13.00),
        (products['vta005'], 5, 9.50),
    ], company)

