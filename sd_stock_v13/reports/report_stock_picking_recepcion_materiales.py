from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import base64
class SdStockPickingRecepcionMateriales(models.Model):
    _inherit = 'stock.picking'


    # def action_button_imprimir_comprobante(self):
    #     """prueba imprimir"""
    #     return self.env.ref('sd_comprobantes_contable.sd_action_account_move_comprobantes').sudo().report_action(self)
    def get_nombre_file_report_comprobante_contable(self):
        """ Retorna el nombre del archivo"""
        name = self.name
        # pdf_adjunto = self.crear_archivo_adjunto()
        # nombre_formato = self.get_name_formato()
        # if not self.state == 'done':
        #     raise UserError(_("El documento debe de estar realizado."))
        # crear archivo adjunto factura/asiento normal
        # self.guardar_archivo_adjunto('Comprobante '+name, pdf_adjunto)
        return str('Recepción de Materiales')

    def get_title_report_comprobante(self):
        """Retornar el tipo del reporte segun su tipo de asiento o factura"""
        titulo = 'RECEPCION DE MATERIALES'
        return titulo

    def get_name_formato(self):
        """Retornar Nombre formato"""
        if self.name:
            array_cadena = self.name.split('/')[::-1]
            array_cadena.pop()
            nombre_final = "_".join(array_cadena)
        else:
            nombre_final = ' '
        return nombre_final

    def crear_archivo_adjunto(self):
        pdf = self.env.ref('sd_comprobantes_contable.sd_action_account_move_comprobantes').render_qweb_pdf(self.ids)
        b64_pdf = base64.b64encode(pdf[0])
        return b64_pdf

    def guardar_archivo_adjunto(self,nombre,b64_pdf):
        """Guardar archivo adjunto en la factura/asiento"""
        self.env['ir.attachment'].create({
            'name': nombre,
            'type': 'binary',
            'datas': b64_pdf,
            'store_fname': nombre,
            'res_model': self._name,
            'res_id': self.id,
            'public': True,
            'mimetype': 'application/pdf'
        })
        return b64_pdf

    def fecha_a_palabras(self):
        date = self.scheduled_date
        if date:
            diccionario = {
                '01': 'enero',
                '02': 'febrero',
                '03': 'marzo',
                '04': 'abril',
                '05': 'mayo',
                '06': 'junio',
                '07': 'julio',
                '08': 'agosto',
                '09': 'septiembre',
                '10': 'octubre',
                '11': 'noviembre',
                '12': 'diciembre',
            }
            return date.strftime("%d") + ' DE ' + diccionario[date.strftime("%m")].upper() + ' DEL ' + date.strftime("%Y")
        else:
            return 'No definido'

    def get_return_total_linea_add(self):
        """Total de lineas adicionales"""
        return self.return_linea_add_report(len(self.line_ids))
    def get_return_total_lineas(self):
        return len(self.line_ids) % 14
    def return_linea_add_report(self,cantidad_lineas):
        if cantidad_lineas <= 14:
            if cantidad_lineas == 14:
                return 0
            else:
                add_linea = 14 - cantidad_lineas
                return add_linea
        else:
            add_linea = 14 - (cantidad_lineas % 14)
            return add_linea
    def get_tasa_cambio(self):
        """RETORNAR TASA DE  CAMBIO"""
        return '6.96'
    def return_order_line_ids(self):
        order_line = sorted(self.move_ids_without_package, key=lambda l: l.id)
        array_lines = []
        for line in order_line:
            if line.quantity_done != 0 or line.product_uom_qty != 0:
                array_lines.append(line)
        print('array: ', array_lines)
        return array_lines

    def numero_to_letras(self, numero):
        indicador = [("", ""), ("MIL", "MIL"), ("MILLON", "MILLONES"), ("MIL", "MIL"), ("BILLON", "BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero) * 100))
        # print 'decimal : ',decimal
        contador = 0
        numero_letras = ""
        while entero > 0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a, 1).strip()
            else:
                en_letras = self.convierte_cifra(a, 0).strip()
            if a == 0:
                numero_letras = en_letras + " " + numero_letras
            elif a == 1:
                if contador in (1, 3):
                    numero_letras = indicador[contador][0] + " " + numero_letras
                else:
                    numero_letras = en_letras + " " + indicador[contador][0] + " " + numero_letras
            else:
                numero_letras = en_letras + " " + indicador[contador][1] + " " + numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        diccionario_Decimal = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
        if decimal in diccionario_Decimal:
            numero_letras = numero_letras + " " + '0' + str(decimal) + "/100"
        else:
            numero_letras = numero_letras + " " + str(decimal) + "/100"
        return numero_letras

    def convierte_cifra(self, numero, sw):
        lista_centana = ["", ("CIEN", "CIENTO"), "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                         "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
        lista_decena = ["", (
            "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"),
                        ("VEINTE", "VEINTI"), ("TREINTA", "TREINTA Y "), ("CUARENTA", "CUARENTA Y "),
                        ("CINCUENTA", "CINCUENTA Y "), ("SESENTA", "SESENTA Y "),
                        ("SETENTA", "SETENTA Y "), ("OCHENTA", "OCHENTA Y "),
                        ("NOVENTA", "NOVENTA Y ")
                        ]
        lista_unidad = ["", ("UN", "UNO"), "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
        centena = int(numero / 100)
        decena = int((numero - (centena * 100)) / 10)
        unidad = int(numero - (centena * 100 + decena * 10))
        # print "centena: ",centena, "decena: ",decena,'unidad: ',unidad

        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""

        # Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad) != 0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]

        # Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        # Validar las unidades
        # print "texto_unidad: ",texto_unidad
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        return "%s %s %s" % (texto_centena, texto_decena, texto_unidad)

    def result_total_debit(self):
        result_total = 0.00
        for line_id in self.line_ids:
            result_total += abs(line_id.debit)
        return round(result_total, 2)

    def result_total_debit2(self):
        result_total = 0
        for line_id in self.move_ids_without_package:
            if line_id.quantity_done == 0:
                result_total += line_id.product_uom_qty
            result_total += line_id.quantity_done
        # return "{:,.2f}".format(round(result_total, 2))
        return str(result_total)

    def result_total_credit(self):
        result_total = 0.00
        for line_id in self.line_ids:
            result_total += abs(line_id.credit)
        return round(result_total, 2)

    def result_total_credit2(self):
        result_total = 0.00
        for line_id in self.line_ids:
            result_total += abs(line_id.credit)
        return "{:,.2f}".format(round(result_total, 2))

    def has_store_id(self):
        # print('bienvenido a la funcion has_store_id, tiene reservacion?')
        if hasattr(self.env['account.journal'], 'store_id'):
            # Field exists, do something
            return True
        else:
            # Field does not exist
            return False

    def getporcentaje(self):
        porcentaje = self.sd_porcentaje
        if not porcentaje:
            porcentaje = ''
        if '%' not in porcentaje and porcentaje:
            porcentaje += '%'

        return porcentaje

    # def filtrar_grupo_analitico(self, grupos):
    #     lineas = []
    #     for line in self.line_ids:
    #         if line.analytic_account_id:
    #             if line.analytic_account_id.group_id.id in grupos:
    #                 lineas.append(line)
    #     print('grupo ', grupos, ': ', lineas)


# class BalancesheetReport(models.AbstractModel):
#     _name = 'report.bi_financial_pdf_reports.report_balancesheet'
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         return {
#             'doc_ids': docids,
#             'doc_model': 'accounting.report.bi',
#             'data': data,
#         }

