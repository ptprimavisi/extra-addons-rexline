from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import io
import xlwt
import tempfile
import os
import xlsxwriter
import base64


class ReportManpower(models.TransientModel):
    _name = 'report.manpower'

    sale_id = fields.Many2one('sale.order')
    excel_file = fields.Binary(string='Excel File', readonly=True)

    def generate_excel(self,company_name, order_name, list_manpower):
        # Create a new workbook
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')

        # Custom palette for background color
        xlwt.add_palette_colour("custom_blue", 0x21)
        workbook.set_colour_RGB(0x21, 3, 40, 89)  # RGB for #032859

        # Styles
        title_style = xlwt.easyxf('font: bold on, height 240; align: horiz center')
        header_style = xlwt.easyxf(
            'font: bold on, colour white; '
            'borders: bottom thin; align: horiz center; '
            'pattern: pattern solid, fore_colour custom_blue;'
        )
        cell_style = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin')
        cell_style_center = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; align: horiz center')
        bold_cell_style = xlwt.easyxf('font: bold on')

        # Set column widths
        worksheet.col(0).width = 5000
        worksheet.col(1).width = 8000
        worksheet.col(2).width = 4000

        # Add title
        worksheet.write_merge(0, 0, 0, 2, company_name, title_style)
        worksheet.write_merge(1, 1, 0, 2, "MANPOWER", title_style)

        # Add order name
        worksheet.write(3, 0, "Sale Order#", bold_cell_style)
        worksheet.write(3, 1, order_name, bold_cell_style)

        # Add table header
        worksheet.write(5, 0, "EMPLOYEE", header_style)
        worksheet.write(5, 1, "POSITION", header_style)
        worksheet.write(5, 2, "WORK HOUR", header_style)

        # Add data rows
        row = 6
        for manpower in list_manpower:
            worksheet.write(row, 0, manpower['employee'], cell_style)
            worksheet.write(row, 1, manpower['position'], cell_style)
            worksheet.write(row, 2, manpower['work_hour'], cell_style_center)
            row += 1

        # Save the workbook to a temporary file
        excel_file_path = tempfile.NamedTemporaryFile(delete=False).name + '.xls'
        workbook.save(excel_file_path)

        # Read the Excel file content
        with open(excel_file_path, 'rb') as file:
            excel_file_content = file.read()

        # Remove the temporary file
        os.remove(excel_file_path)

        # Encode the file content to base64 for returning
        return base64.b64encode(excel_file_content).decode()



    def action_generate(self):
        for line in self:
            # for line in self:
            so = line.sale_id
            # line.mrp_production_count = 0
            ids = []
            if so:
                mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
                for mos in mo:
                    ids.append(mos.id)
                    sub_mo_ids = mos._get_children().ids
                    order1 = self.env['mrp.production'].search([('id', 'in', sub_mo_ids)])
                    if order1:
                        for moss in order1:
                            ids.append(moss.id)
                            order2 = self.env['mrp.production'].search([('id', 'in', moss._get_children().ids)])
                            if order2:
                                for mosss in order2:
                                    ids.append(mosss.id)
                                    order3 = self.env['mrp.production'].search(
                                        [('id', 'in', mosss._get_children().ids)])
                                    if order3:
                                        for mossss in order3:
                                            ids.append(mossss.id)
                                            order4 = self.env['mrp.production'].search(
                                                [('id', 'in', mossss._get_children().ids)])
                                            if order4:
                                                for mosssss in order4:
                                                    ids.append(mosssss.id)
            prod_report = self.env['production.report'].search([('mo_id','in',ids),('state','=','done')])
            manpower_ids = []
            
            # Get Manpower
            list_manpower = []
            if prod_report:
                manpower = self.env['man.power.line'].search([('report_id.schedule_id','in', prod_report.ids)])
                for mans in manpower:
                    list_manpower.append({
                        'employee': mans.employee_id.name,
                        'position': mans.position,
                        'work_hour': mans.work_hours
                    })

            # Get Company Profile
            company = self.env.user.company_id

            company_name = company.partner_id.name or ''
            company_street1 = company.partner_id.street or ''
            company_street2 = company.partner_id.street2 or ''
            company_street3 = (
                str(company.partner_id.city or '') + ', ' +
                str(company.partner_id.state_id.name or '') + ', ' +
                str(company.partner_id.country_id.name or '') + ', ' +
                str(company.partner_id.zip or '')
            )
            company_npwp = company.partner_id.vat or ''
            company_phone = company.partner_id.phone or ''
            company_web = company.partner_id.website or ''
            
            # Get Sale Order Name
            order_name = line.sale_id.name

            # Generate Excel
            generate_excel = self.generate_excel(company_name,order_name,list_manpower)
            filename = f"manpower-{order_name}.xls"
            line.excel_file = generate_excel
            return {
                    'type': 'ir.actions.act_url',
                    'url': f'web/content/?model=report.manpower&id={line.id}&field=excel_file&download=true&filename={filename}',
                    'target': 'new',
            }




