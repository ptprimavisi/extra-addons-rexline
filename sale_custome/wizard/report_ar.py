from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import io
import xlsxwriter
import base64


class ReportAr(models.TransientModel):
    _name = 'report.ar'

    date_from = fields.Date()
    date_to = fields.Date()

    def get_data(self):
        for line in self:
            if line.date_from > line.date_to:
                raise UserError('Tanggal Mulai Harus lebih Kecil')
            # list = []
            invoice_before = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('payment_state', 'in', ['partial', 'not_paid']), ('invoice_date', '<', line.date_from)])
            # invoice_before_notpaid = self.env['account.move'].search([('state','=', 'posted'), ('move_type','=','out_invoice'), ('payment_state','=','not_paid'), ('invoice_date','<', line.date_from), ('amount_residual_signed','=',0)])

            invoice_before = sum(invoice_before.mapped('amount_residual_signed'))
            # notpaid_before = sum(invoice_before_notpaid.mapped('amount_total'))

            invoice_afters = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('payment_state', 'in', ['partial', 'not_paid']), ('invoice_date', '>=', line.date_from),
                 ('invoice_date', '<=', line.date_to)])
            invoice_after = sum(invoice_afters.mapped('amount_total'))
            pembayaran = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('payment_state', 'in', ['partial', 'paid']), ('invoice_date', '>=', line.date_from),
                 ('invoice_date', '<=', line.date_to)])
            total_bayar = 0
            for lines in pembayaran:
                if lines.payment_state == 'paid':
                    total_bayar += lines.amount_total
                elif lines.payment_state == 'partial':
                    amount = lines.amount_total - lines.amount_residual_signed
                    total_bayar += amount

            list = {
                'saldo_awal': invoice_before,
                'piutang_baru': invoice_after,
                'pembayaran': total_bayar,
                'saldo_akhir': (invoice_before + invoice_after) - total_bayar,
                'line': []
            }
            for inv_line in invoice_afters:
                list['line'].append(
                    {
                        'name': inv_line.name,
                        'partner': inv_line.partner_id.name,
                        'amount': inv_line.amount_total,
                        'amount_due': inv_line.amount_residual_signed,
                        'origin': inv_line.invoice_origin,
                        'date': inv_line.invoice_date
                    }
                )
            # print(list)
            # exit()
            return list

    def generate_excel(self):
        for line in self:
            output = io.BytesIO()

            # Membuat workbook dan worksheet
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet()
            style_header = workbook.add_format(
                {'bold': True, 'bg_color': '#f50a0a', 'font_color': 'white', 'align': 'center', 'border': 1})
            worksheet.merge_range(0,3,0,5, 'REPORT ACCOUNT RECEPTABLE', style_header)
            header_format = workbook.add_format({'bold': True, 'border': 1})
            worksheet.set_column(1, 0, 5)
            worksheet.set_column(1, 1, 30)
            worksheet.set_column(1, 2, 18)
            worksheet.set_column(1, 3, 18)
            worksheet.set_column(6, 4, 30)
            worksheet.set_column(6, 5, 30)
            worksheet.set_column(6, 6, 30)

            worksheet.write(1, 1, 'SALDO AWAL', header_format)
            worksheet.write(2, 1, 'PIUTANG BARU', header_format)
            worksheet.write(3, 1, 'PEMBAYARAN', header_format)
            worksheet.write(4, 1, 'SALDO AKHIR', header_format)

            data = self.get_data()

            worksheet.write(1, 2, data['saldo_awal'], header_format)
            worksheet.write(2, 2, data['piutang_baru'], header_format)
            worksheet.write(3, 2, data['pembayaran'], header_format)
            worksheet.write(4, 2, data['saldo_akhir'], header_format)

            sub_header = workbook.add_format(
                {'bg_color': '#235391', 'font_color': 'white', 'align': 'center', 'border': 1})

            worksheet.write(6, 0, 'No', sub_header)
            worksheet.write(6, 1, 'Number', sub_header)
            worksheet.write(6, 2, 'Customer ', sub_header)
            worksheet.write(6, 3, 'Date', sub_header)
            worksheet.write(6, 4, 'Reference', sub_header)
            worksheet.write(6, 5, 'Amount Total', sub_header)
            worksheet.write(6, 6, 'Amount Due', sub_header)

            body_format = workbook.add_format({'border': 1})
            date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy/mm/dd'})
            row = 7
            no = 1
            for inv_line in data['line']:
                worksheet.write(row, 0, no, body_format)
                worksheet.write(row, 1, inv_line['name'], body_format)
                worksheet.write(row, 2, inv_line['partner'], body_format)
                worksheet.write(row, 3, inv_line['date'], date_format)
                worksheet.write(row, 4, inv_line['origin'], body_format)
                worksheet.write(row, 5, '{:,.2f}'.format(inv_line['amount']), body_format)
                worksheet.write(row, 6, '{:,.2f}'.format(inv_line['amount_due']), body_format)
                row += 1
                no += 1


            workbook.close()

            # Mendapatkan konten dari buffer
            excel_file = output.getvalue()
            output.close()
            return excel_file

    def action_generate(self):
        # Membuat buffer untuk menyimpan file Excel
        excel_file = self.generate_excel()

        # Mengkodekan file menjadi base64
        file_base64 = base64.b64encode(excel_file)

        # Membuat attachment untuk menyimpan file di database
        attachment = self.env['ir.attachment'].create({
            'name': 'report account receptable.xlsx',
            'type': 'binary',
            'datas': file_base64,
            'store_fname': 'report_account_receiptable.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'self',
        }
