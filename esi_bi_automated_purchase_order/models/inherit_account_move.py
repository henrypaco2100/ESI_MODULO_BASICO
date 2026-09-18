from odoo import models, fields, api, _

class InheritAccountMoveAutoSale(models.Model):
    _inherit = 'account.move'
    _descripcion = 'Henrencia para el Automated Sale'
    sd_numero_recibo_purchase = fields.Char(string='Nro Recibo')
    sd_is_numero_recibo_purchase = fields.Boolean(default=False)
    sd_numero_factura_purchase = fields.Char(string='Nro Factura')
    sd_is_numero_factura_purchase = fields.Boolean(default=False)
    sd_ref_entrega = fields.Char(string='Nota de Entrega')
    sd_is_ref = fields.Boolean(default=False)
    sd_nro_importacion = fields.Char(string='Nro Importación')
    sd_is_nro_importacion = fields.Boolean(default=False)

    # facturacion compra
    fcb_autorizacion_compra = fields.Char(string="Numero de Autorizacion",copy=False)
    fcb_codigo_control_compra = fields.Char(string="Codigo de Control",copy=False)
    fcb_numero_dim = fields.Char(string="Numero de Declaracion de Importacion",copy=False)
    fcb_numero_factura = fields.Char(string="Numero de Factura",copy=False)
    fcb_cuf = fields.Char(string="CUF",copy=False)
    fcb_link = fields.Char(string='URL',copy=False)
    fcb_tipo_compra = fields.Selection([
        ('compra_interno_gravadas', 'Compras para mercado interno con destino a actividades gravadas'),
        ('compra_interno_no_gravadas', 'Compras para mercado interno con destino a actividades no gravadas,'),
        ('compra_proporcionalidad', 'Compras sujetas a proporcionalidad'),
        ('compra_exportaciones', 'Compras para exportaciones'),
        ('compra_interno_exportaciones', 'Compras tanto para el mercado interno como para exportaciones'),
    ],
        string='Factura de Compras',copy=False)
    fcb_es_factura_compra = fields.Boolean(string='Facturación Compra',copy=False)

    sd_numero_dui = fields.Char(string="DUI")
    sd_codigo_aduana = fields.Selection([
        ('071', '071 Agencia Exterior Matarani'),
        ('072', '072 Agencia Exterior Arica'),
        ('073', '073 Agencia Exterior Matarani-Ilo'),
        ('101', '101 Interior Sucre'),
        ('102', '102 Especializada Interior Sucre'),
        ('111', '111 Aeropuerto Sucre'),
        ('201', '201 Interior La Paz'),
        ('202', '202 Especializada Interior La Paz'),
        ('211', '211 Aeropuerto El Alto'),
        ('221', '221 Frontera Chara¤a'),
        ('231', '231 Zona Franca Comercial El Alto'),
        ('232', '232 Zona Franca Industrial El Alto'),
        ('233', '233 Zona Franca Comercial Desaguadero'),
        ('234', '234 Zona Franca Industrial Patacamaya'),
        ('235', '235 Zona Franca Comercial Patacamaya'),
        ('241', '241 Frontera Desaguadero'),
        ('242', '242 Frontera Kasani'),
        ('243', '243 CEBAF Desaguadero'),
        ('244', '244 Frontera Puerto Acosta'),
        ('261', '261 Postal La Paz'),
        ('301', '301 Interior Cochabamba'),
        ('302', '302 Especializada Interior Cochabamba'),
        ('311', '311 Aeropuerto Cochabamba'),
        ('331', '331 Zona Franca Comercial Cochabamba'),
        ('332', '332 Zona Franca Industrial Cochabamba'),
        ('361', '361 Postal Cochabamba'),
        ('401', '401 Interior Oruro'),
        ('402', '402 Especializada Interior Oruro'),
        ('421', '421 Frontera Pisiga'),
        ('422', '422 Frontera Tambo Quemado'),
        ('431', '431 Zona Franca Comercial Oruro'),
        ('432', '432 Zona Franca Industrial Oruro'),
        ('501', '501 Interior Potosi'),
        ('502', '502 Especializada Interior Potosi'),
        ('521', '521 Frontera Villaz¢n'),
        ('522', '522 ACI Villaz¢n'),
        ('531', '531 Zona Franca Comercial Villaz¢n'),
        ('542', '542 Frontera Apacheta/Hito Cajones'),
        ('543', '543 Frontera Avaroa'),
        ('601', '601 Interior Tarija'),
        ('602', '602 Especializada Interior Tarija'),
        ('611', '611 Aeropuerto Tarija'),
        ('621', '621 Frontera Yacuiba'),
        ('622', '622 Frontera Picada Sucre'),
        ('623', '623 ACI Yacuiba'),
        ('631', '631 Zona Franca Comercial Yacuiba'),
        ('641', '641 Frontera Bermejo'),
        ('642', '642 ACI Bermejo'),
        ('643', '643 Frontera Ca¤ada Oruro'),
        ('701', '701 Interior Santa Cruz'),
        ('702', '702 Especializada Interior Santa Cruz'),
        ('711', '711 Aeropuerto Viru-Viru'),
        ('712', '712 Aeropuerto Puerto Suarez'),
        ('721', '721 Frontera Puerto Suarez'),
        ('722', '722 Frontera Arroyo Concepcion'),
        ('723', '723 Punto de Control "El Faro"'),
        ('731', '731 Zona Franca Comercial Pto. Aguirre'),
        ('732', '732 Zona Franca Comercial Santa Cruz'),
        ('733', '733 Zona Franca Comercial San Matias'),
        ('734', '734 Zona Franca Comercial Pto. Suarez'),
        ('735', '735 Zona Franca Comercial Winner'),
        ('736', '736 Zona Franca Industrial Pto. Suarez'),
        ('737', '737 Zona Franca Winner'),
        ('738', '738 Zona Franca Industrial Santa Cruz'),
        ('741', '741 Frontera San Matias'),
        ('743', '743 Frontera San Vicente'),
        ('751', '751 Fluvial Puerto Jennefer'),
        ('752', '752 Punto de Control "El Faro"'),
        ('761', '761 Postal Santa Cruz'),
        ('801', '801 Interior Trinidad'),
        ('831', '831 Zona Franca Comercial Guayaramerin'),
        ('841', '841 Frontera Guayaramerin'),
        ('842', '842 Punto de controL(ACI)Guajara-Mirim'),
        ('862', '862 Postal Trinidad'),
        ('911', '911 Aeropuerto Cobija'),
        ('921', '921 Frontera Cobija'),
        ('931', '931 Zona Franca Comercial e Ind.Cobija'), ], string='Aduana Destino')

