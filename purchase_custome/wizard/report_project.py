from odoo import models, fields, api
from odoo.exceptions import UserError
from io import BytesIO
import base64
import xlwt
import os
import io
import xlsxwriter
import tempfile
from odoo.http import content_disposition, request
from werkzeug.wrappers import Response


class ReportBudgetProject(models.TransientModel):
    _name = 'report.budget.project'

    inquiry_id = fields.Many2one('inquiry.inquiry')

    def get_data(self):
        for line in self:
            result = []
            inquiry = self.env['inquiry.inquiry'].search([('id', '=', int(line.inquiry_id.id))])
            if inquiry:
                for lines in inquiry.inquiry_line_detail:
                    mrf = self.env['mrf.mrf'].search([('inquiry_id','=',int(inquiry.id))])
                    mrf_ids = []
                    for mrfs in mrf:
                        mrf_ids.append(mrfs.id)
                    mrf_line = self.env['mrf.line'].search([('product_id','=',lines.product_id.id), ('mrf_id','in',mrf_ids)])
                    budget_price = sum(mrf_line.mapped('budget'))
                    budget_total = sum(mrf_line.mapped('budget')) * sum(mrf_line.mapped('quantity'))
                    qty_purchase = sum(mrf_line.mapped('qty_ordered'))
                    purchase_line = self.env['purchase.order.line'].search(
                        [('order_id.mrf_id','in',mrf_ids), ('state', '=', 'purchase'),
                         ('product_id', '=', lines.product_id.id), ('qty_received','!=',0)])
                    purchase_price = self.env['purchase.order.line'].search(
                        [('order_id.mrf_id','in',mrf_ids), ('state', '=', 'purchase'),
                         ('product_id', '=', lines.product_id.id), ('qty_received','!=',0)], limit=1)
                    total_price_po = purchase_price.price_unit * sum(purchase_line.mapped('qty_received'))
                    purchase_ids = []
                    for purshases in purchase_line:
                        purchase_ids.append(purshases.order_id.id)
                    purchase = self.env['purchase.order'].search([('id','in', purchase_ids)])
                    po_name = ','.join([line.name for line in purchase])

                    result.append({
                        'product': lines.product_id.name,
                        'uom': lines.product_uom.name,
                        'qty': lines.product_uom_quantity,
                        'unit_price': lines.cost_price,
                        'total_price': lines.subtotal,
                        'budget_price': budget_price,
                        'budget_total': budget_total,
                        'qty_purchase': qty_purchase,
                        'po_price': purchase_price.price_unit,
                        'total_price_po': total_price_po,
                        'po_number': po_name,

                    })
            else:
                raise UserError('Inquiry Not Found')
            return result

    def generate_excel(self):
        output = io.BytesIO()

        # Membuat workbook dan worksheet
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # header_format = workbook.add_format({'bold': True,'bg_color': '#FFA07A'})
        header_format = workbook.add_format({'bold': True,'border': 1})
        worksheet.set_column(1, 0, 5)
        worksheet.set_column(1, 1, 30)
        worksheet.set_column(1, 2, 18)
        # y, x
        # Contoh isi dari Excel
        inquiry = self.env['inquiry.inquiry'].search([('id','=', self.inquiry_id.id)])
        so = self.env['sale.order'].search([('state','=', 'sale'),('opportunity_id','=', self.inquiry_id.opportunity_id.id)], limit=1)
        so_name = str(so.name) or 'Unknown'
        # worksheet.write(0, 0, 'N.')
        worksheet.write(1, 1, 'CUSTOMER NAME', str(inquiry.partner_id.name))
        worksheet.write(2, 1, 'PROJECT NO', str(inquiry.name))
        worksheet.write(3, 1, '', header_format)
        worksheet.write(4, 1, so_name, header_format)

        worksheet.write(1, 2, 'PT SURYA PALOH', header_format)
        worksheet.write(2, 2, 'INQ/REX/0001', header_format)
        worksheet.write(3, 2, 'KALIMANTAN', header_format)
        worksheet.write(4, 2, 'S00009', header_format)

        style_header = workbook.add_format(
            {'bold': True, 'bg_color': '#f50a0a', 'font_color': 'white', 'align': 'center','border': 1   })
        sub_header = workbook.add_format(
            {'bg_color': '#235391', 'font_color': 'white', 'align': 'center','border': 1   })
        # merge_range(first_row, first_col, last_row, last_col, data, cell_format)

        worksheet.merge_range(5, 5, 5, 8, 'BOQ from Engineering', style_header)
        worksheet.merge_range(5, 9, 5, 10, 'Budget from Cost Control', style_header)
        worksheet.merge_range(5, 11, 5, 16, 'Actual From Purchasing', style_header)

        worksheet.write(6, 0, 'No', sub_header)
        worksheet.write(6, 1, 'Item Name', sub_header)
        worksheet.write(6, 2, 'Detailed Specification ', sub_header)
        worksheet.write(6, 3, 'Phase', sub_header)
        worksheet.write(6, 4, 'Brand', sub_header)

        worksheet.write(6, 5, 'UoM', sub_header)
        worksheet.write(6, 6, 'Qty', sub_header)
        worksheet.write(6, 7, 'Unit Price', sub_header)
        worksheet.write(6, 8, 'Total Price', sub_header)

        worksheet.write(6, 9, 'Unit Price', sub_header)
        worksheet.write(6, 10, 'Total Price', sub_header)

        worksheet.write(6, 11, 'UoM', sub_header)
        worksheet.write(6, 12, 'Qty', sub_header)
        worksheet.write(6, 13, 'Unit Price', sub_header)
        worksheet.write(6, 14, 'Total Price', sub_header)
        worksheet.write(6, 15, 'PO No', sub_header)
        worksheet.write(6, 16, 'Status', sub_header)

        # data = self.get_report_data()  # method yang mengambil data yang akan ditampilkan
        result = self.get_data()
        body_format = workbook.add_format({'border': 1})
        row = 7
        no = 1
        for index in result:
            worksheet.write(row, 0, no,body_format)
            worksheet.write(row, 1,  index['product'],body_format)
            worksheet.write(row, 2,  '',body_format)
            worksheet.write(row, 3,  '',body_format)
            worksheet.write(row, 4,  '',body_format)
            worksheet.write(row, 5,  index['uom'],body_format)
            worksheet.write(row, 6,  index['qty'],body_format)
            worksheet.write(row, 7,  '{:,.2f}'.format(index['unit_price']),body_format)
            worksheet.write(row, 8,  '{:,.2f}'.format(index['total_price']),body_format)
            worksheet.write(row, 9,  '{:,.2f}'.format(index['budget_price']),body_format)
            worksheet.write(row, 10,  '{:,.2f}'.format(index['budget_total']),body_format)
            worksheet.write(row, 11, index['uom'], body_format)
            worksheet.write(row, 12, index['qty_purchase'], body_format)
            worksheet.write(row, 13, '{:,.2f}'.format(index['po_price']), body_format)
            worksheet.write(row, 14, '{:,.2f}'.format(index['total_price_po']), body_format)
            worksheet.write(row, 15, index['po_number'], body_format)
            worksheet.write(row, 16, '', body_format)
            # worksheet.write(row, 2, f'Desc {no}',body_format)
            row += 1
            no += 1

        # Menutup workbook
        workbook.close()

        # Mendapatkan konten dari buffer
        excel_file = output.getvalue()
        output.close()
        return excel_file

    def action_print_report(self):
        # Membuat buffer untuk menyimpan file Excel
        excel_file = self.generate_excel()

        # Mengkodekan file menjadi base64
        file_base64 = base64.b64encode(excel_file)

        # Membuat attachment untuk menyimpan file di database
        attachment = self.env['ir.attachment'].create({
            'name': 'report.xlsx',
            'type': 'binary',
            'datas': file_base64,
            'store_fname': 'report_budget.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'self',
        }
