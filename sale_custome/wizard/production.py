from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import io
import xlwt
import tempfile
import os
import xlsxwriter
import base64
from PIL import Image
from io import BytesIO
from xlwt import easyxf


class ManufacturWizard(models.TransientModel):
    _name = 'manufactur.wizard'

    product_id = fields.Many2one('product.product')
    schedule_date = fields.Datetime()
    product_qty = fields.Float()
    warehouse_id = fields.Many2one('stock.warehouse')
    origin = fields.Char()

    def default_get(self, fields_list):
        defaults = super(ManufacturWizard, self).default_get(fields_list)

        product_id = self.env.context.get('product_id', False)
        Schedule_date = self.env.context.get('schedule_date', False)
        product_qty = self.env.context.get('product_qty', False)
        origin = self.env.context.get('origin', False)
        if product_id:
            defaults['product_id'] = product_id
            defaults['schedule_date'] = Schedule_date
            defaults['product_qty'] = product_qty
            defaults['origin'] = origin

        return defaults

    def action_save(self):
        for line in self:
            mo = self.env['mrp.production'].search([])
            picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',line.warehouse_id.id),('code','=','mrp_operation')])
            create_mo = mo.create({
                'product_id': int(line.product_id.id),
                'product_qty': line.product_qty,
                'origin': str(line.origin),
                'picking_type_id': picking_type.id,
                'state': 'draft'
            })
            if create_mo:
                create_mo.action_confirm()
            if create_mo:
                inquiry_id = self.env.context.get('inquiry_id', False)
                inquiry = self.env['inquiry.inquiry'].search([('id','=',int(inquiry_id))])
                if inquiry:
                    inquiry.action_compute_task()


class GeneralDailyReport(models.TransientModel):
    _name = 'general.daily.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'general.daily.report')],
        string='Attachments'
    )
    schedule_id = fields.Many2one('production.report')
    partner_id = fields.Many2one('res.partner')
    sale_id = fields.Many2one('sale.order')
    location = fields.Char()
    date = fields.Date()
    man_power_ids = fields.One2many('man.power.line', 'report_id')
    problem_ids = fields.One2many('problem.line', 'report_id')
    solving_ids = fields.One2many('solving.line', 'report_id')
    target_ids = fields.One2many('target.line', 'report_id')
    excel_file = fields.Binary(string='Excel File', readonly=True)

    def action_print(self):
        for line in self:
            # raise UserError(line.tax_list)
            return self.env.ref('sale_custome.action_report_daily_report').with_context(
                paperformat=4, landscape=False).report_action(self)

    def action_print_excel(self):
        for rec in self:
            # raise UserError('action_print_excel is clicked')
            
            partner = rec.partner_id.name or 'Unknown'
            date = str(rec.date) or 'Unknown'
            project = rec.sale_id.name or 'Unknown'
            location = rec.location or 'Unknown'

            pekerjaan=[]
            numb=0
            for line in rec.man_power_ids:
                numb+=1
                pekerjaan.append([numb,line.employee_id.name or 'Unknown',line.description or 'Unknown',line.p or 'Unknown',line.l or 'Unknown',line.t or 'Unknown',line.quantity or 'Unknown'])

            kendala=[]
            numb=0
            for line in rec.problem_ids:
                numb+=1
                kendala.append([numb,line.description or 'Unknown'])

            solving=[]
            numb=0
            for line in rec.solving_ids:
                numb+=1
                solving.append([numb,line.description or 'Unknown'])

            target=[]
            numb=0
            for line in rec.target_ids:
                numb+=1
                target.append([numb,line.description or 'Unknown'])

            # Create workbook and worksheet
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet('General Daily Report')
            
            # Custom palette for background color
            xlwt.add_palette_colour("custom_blue", 0x21)
            workbook.set_colour_RGB(0x21, 3, 40, 89)  # RGB for #032859

            # Define custom styles
            title_style = xlwt.easyxf('font: bold on, height 300; align: horiz center')
            sub_title_style = xlwt.easyxf('font: bold on, height 240; align: horiz left')
            header_style = xlwt.easyxf(
                'font: bold on, colour white; borders: bottom thin; align: horiz center; '
                'pattern: pattern solid, fore_colour custom_blue;'
            )
            cell_style = xlwt.easyxf('align: horiz left')
            cell_style_center = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; align: horiz center')
            cell_style_left = xlwt.easyxf('borders: left thin, right thin, top thin, bottom thin; align: horiz left')

            # Set column widths
            worksheet.col(0).width = 5000
            worksheet.col(1).width = 6000
            worksheet.col(2).width = 4000
            worksheet.col(3).width = 4000
            worksheet.col(4).width = 4000
            worksheet.col(5).width = 4000
            worksheet.col(6).width = 4000

            # Write header information
            worksheet.write_merge(0, 0, 0, 6, "GENERAL DAILY REPORT", title_style)
            worksheet.write(2, 0, "CUSTOMER / CLIENT", cell_style)
            worksheet.write(2, 1, ": "+partner, cell_style)

            worksheet.write(3, 0, "DATE", cell_style)
            worksheet.write(3, 1, ": "+date, cell_style)

            worksheet.write(4, 0, "SO / PROJECT", cell_style)
            worksheet.write(4, 1, ": "+project, cell_style)

            worksheet.write(5, 0, "LOCATION", cell_style)
            worksheet.write(5, 1, ": "+location, cell_style)

            # Write pekerjaan section
            row = 7
            worksheet.write(row, 0, "A. PEKERJAAN", sub_title_style)
            row += 1
            worksheet.write(row, 0, "NO", header_style)
            worksheet.write(row, 1, "MAN POWER", header_style)
            worksheet.write(row, 2, "KEGIATAN", header_style)
            worksheet.write(row, 3, "P", header_style)
            worksheet.write(row, 4, "L", header_style)
            worksheet.write(row, 5, "T", header_style)
            worksheet.write(row, 6, "QTY", header_style)

            for line in pekerjaan:
                row += 1
                for col, val in enumerate(line):
                    style = cell_style_left if col in [1,2] else cell_style_center
                    worksheet.write(row, col, val, style)

            # Write kendala section
            row += 2
            worksheet.write(row, 0, "B. KENDALA", sub_title_style)
            row += 1
            worksheet.write(row, 0, "NO", header_style)
            worksheet.write(row, 1, "URAIAN", header_style)

            for line in kendala:
                row += 1
                for col, val in enumerate(line):
                    style = cell_style_center if col == 0 else cell_style_left
                    worksheet.write(row, col, val, style)

            # Write solving section
            row += 2
            worksheet.write(row, 0, "C. SOLVING", sub_title_style)
            row += 1
            worksheet.write(row, 0, "NO", header_style)
            worksheet.write(row, 1, "URAIAN", header_style)

            for line in solving:
                row += 1
                for col, val in enumerate(line):
                    style = cell_style_center if col == 0 else cell_style_left
                    worksheet.write(row, col, val, style)

            # Write target section
            row += 2
            worksheet.write(row, 0, "E. TARGET BERIKUTNYA", sub_title_style)
            row += 1
            worksheet.write(row, 0, "NO", header_style)
            worksheet.write(row, 1, "DESKRIPSI PEKERJAAN", header_style)

            for line in target:
                row += 1
                for col, val in enumerate(line):
                    style = cell_style_center if col == 0 else cell_style_left
                    worksheet.write(row, col, val, style)

            # Process attachments and add links (for images) instead of inserting images directly
            row += 2
            worksheet.write(row, 0, "LAMPIRAN", xlwt.easyxf('font: bold on, height 240; align: horiz left'))
            row += 1

            for attachment in rec.attachment_ids:
                if attachment.mimetype.startswith('image'):
                    # Save image to temporary file (PNG)
                    img_data = base64.b64decode(attachment.datas)
                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_img.write(img_data)
                    temp_img.close()

                    # Convert the PNG image to BMP (24-bit true color)
                    with Image.open(temp_img.name) as img:
                        # Get the original image dimensions
                        original_width, original_height = img.size

                        # Resize the image to 50% of its original size
                        new_width = int(original_width * 0.5)
                        new_height = int(original_height * 0.5)
                        # Convert image to RGB (24-bit)
                        img = img.convert('RGB')
                        img = img.resize((new_width, new_height))  # Resize the image
                        bmp_img_path = temp_img.name.replace('.png', '.bmp')
                        img.save(bmp_img_path, 'BMP')

                    # Insert the BMP image into the worksheet
                    worksheet.insert_bitmap(bmp_img_path, row, 0)

                    # Set row height to create space between images (e.g., 300 points height)
                    worksheet.row(row).height = 300  # Adjust this value to control space above the image

                    # Move to the next row (adjust as needed)
                    row += 15

                    # Clean up temporary files
                    os.unlink(temp_img.name)
                    os.unlink(bmp_img_path)

            # Save workbook to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xls')
            workbook.save(temp_file.name)

            # Encode file for download
            with open(temp_file.name, 'rb') as file:
                file_content = file.read()

            rec.excel_file = base64.b64encode(file_content).decode()
            os.unlink(temp_file.name)

            filename = f"dailyreport-{project}.xls"
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/?model={rec._name}&id={rec.id}&field=excel_file&download=true&filename={filename}',
                'target': 'new',
            }


class ManPower(models.TransientModel):
    _name = 'man.power.line'

    employee_id = fields.Many2one('hr.employee')
    description = fields.Many2many('production.tag')
    position = fields.Many2one('hr.job')
    work_hours = fields.Float()
    p = fields.Float()
    t = fields.Float()
    l = fields.Float()
    quantity = fields.Float()
    report_id = fields.Many2one('general.daily.report')

    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            line.position = False
            if line.employee_id:
                if line.employee_id.job_id:
                    line.position = line.employee_id.job_id.id


class ProblemLine(models.TransientModel):
    _name = 'problem.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')


class SolvingLine(models.TransientModel):
    _name = 'solving.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')


class TargetLine(models.TransientModel):
    _name = 'target.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')
