from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import base64

class SdAccountPaymentComprobanteContable(models.Model):
    _inherit = 'account.payment'
    def get_nombre_file_report_comprobante_contable(self):
        """ Retorna el nombre del archivo"""
        print('funcion del titulo')
        if not self.state == 'posted':
            raise UserError(_("El documento debe de estar publicado."))
        name = self.name
        return str('Comprobantes '+name)
    def get_title_report_comprobante(self):
        nombre_formato = self.get_name_formato()
        if self.payment_type=='transfer':
            titulo = 'COMPROBANTE DE TRASPASO ' + self.name
        elif self.payment_type=='inbound':
            titulo = 'COMPROBANTE DE INGRESO ' + self.name
        elif self.payment_type=='outbound':
            titulo = 'COMPROBANTE DE EGRESO ' + self.name
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
        pdf = self.env.ref('sd_comprobantes_contable.sd_action_account_payment_comprobantes').render_qweb_pdf(self.ids)
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
        date = self.payment_date
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
    def get_tasa_cambio(self):
        """RETORNAR TASA DE  CAMBIO"""
        return '6.96'
    def get_return_total_linea_add(self):
        """Total de lineas adicionales"""
        return self.return_linea_add_report(len(self.move_line_ids))
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
    def numero_to_letras(self, numero):
        indicador = [("", ""), ("MIL", "MIL"), ("MILLON", "MILLONES"), ("MIL", "MIL"), ("BILLON", "BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero) * 100))
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
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad) != 0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]
        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        return "%s %s %s" % (texto_centena, texto_decena, texto_unidad)
    def result_total_debit(self):
        result_total = 0
        for line_id in self.move_line_ids:
            result_total += abs(line_id.debit)
        return result_total
    def result_total_credit(self):
        result_total = 0
        for line_id in self.move_line_ids:
            result_total += abs(line_id.credit)
        return result_total
