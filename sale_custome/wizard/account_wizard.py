import base64
import io
from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountWizard(models.TransientModel):
    _name = "account.wizard"
    _description = 'Account Wizard'

    name = fields.Char(default="Invoice", help='Name of Invoice ')
    today = fields.Date("Report Date", default=fields.Date.today, help='Date at which report is generated')
    levels = fields.Selection([
        ('summary', 'Summary'),
        ('consolidated', 'Consolidated'),
        ('detailed', 'Detailed'),
        ('very', 'Very Detailed')],
        string='Levels', required=True, default='summary',
        help='Different levels for cash flow statements')
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries')],
        string='Target Moves', required=True, default='posted', help='Type of entries')
    batch_id = fields.Many2one('hr.payslip.run', string='Payslip Batch', required=True)
    excel_file = fields.Binary(string='Excel File', readonly=True)

    def generate_gaji(self):
        for rec in self:
            generate_excel = self.get_xlsx_report_mingguan()
            rec.excel_file = generate_excel
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=account.wizard&id={}&field=excel_file&download=true&filename=laporan_gaji.xlsx'.format(
                    rec.id),
                'target': 'new',
            }

    def get_xlsx_report_mingguan(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        rupiah_format = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1, 'align': 'center'})
        bold_format = workbook.add_format({'bold': True, 'align': 'center', 'num_format': 'Rp #,##0', 'border': 1})
        align_header = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
        align = workbook.add_format({'align': 'center', 'border': 1})
        align_center = workbook.add_format({'align': 'center', 'bold': True})
        sheet = workbook.add_worksheet()

        current_date = datetime.now()
        month_year_text = f'PERIODE  {current_date.strftime("%B").upper()} {current_date.strftime("%Y")}'

        if self.batch_id:
            sheet.merge_range('G1:M1', 'UPAH KARYAWAN', align_center)
            sheet.merge_range('G2:M2', month_year_text, align_center)
            headers = [
                "NAMA KARYAWAN", "PAYSLIP BATCHES", "DATE FROM", "DATE TO", "PTKP", "BASIC SALARY", "HOUSE RENT ALLOWANCE",
                "SITE ALLOWANCE", "OVERTIME", "BACKPACK SALARY", "MEAL ALLOWANCE (SITE)", "SITE ALLOWANCE (SITE)",
                "TRAVEL ALLOWANCE", "MEAL ALLOWANCE", "JHT EMPLOYEE ALLOWANCE", "BPJSK ALLOWANCE EMPLOYEE",
                "MISCELLANEOUS BENEFITS", "POSITION ALLOWANCE", "ABSENCE DEDUCTIONS", "MISCELLANEOUS DEDUCTIONS",
                "PPH 21", "JHT EMPLOYEES", "GROSS", "NET", "BANK ACCOUNT"
            ]
            for col, title in enumerate(headers):
                sheet.write(3, col, title, align_header)

            no = 3
            query = """
                SELECT a.employee_id, a.id 
                FROM hr_payslip a 
                JOIN hr_employee e ON a.employee_id = e.id 
                WHERE a.payslip_run_id = %s
            """
            self._cr.execute(query, (self.batch_id.id,))
            payslip_data = self._cr.dictfetchall()

            for line in payslip_data:
                no += 1
                employee = self.env['hr.employee'].browse(line['employee_id'])
                payslip = self.env['hr.payslip'].browse(line['id'])
                batch_name = payslip.payslip_run_id.name or ''
                date_from = payslip.payslip_run_id.date_start.strftime(
                    '%Y-%m-%d') if payslip.payslip_run_id.date_start else ''
                date_to = payslip.payslip_run_id.date_end.strftime(
                    '%Y-%m-%d') if payslip.payslip_run_id.date_end else ''
                contract = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('state', '=', 'open')], limit=1)
                ptkp = contract.ptkp_id.name if contract and contract.ptkp_id else ''
                bank_account = payslip.employee_id.bank_account_id
                bank_num = f"{bank_account.acc_number} - {bank_account.bank_id.name}" if bank_account else ''

                self._cr.execute("SELECT code, amount FROM hr_payslip_line WHERE slip_id = %s", (line['id'],))
                result_lines = self._cr.dictfetchall()

                amounts = {
                    'BASIC': 0.0, 'HRA': 0.0, 'STALW': 0.0, 'OVT': 0.0, 'BPSL': 0.0, 'MALLSITE': 0.0,
                    'STALLSITE': 0.0, 'Travel': 0.0, 'Meal': 0.0, 'JHTALW': 0.0, 'BPJSALW': 0.0,
                    'MSCB': 0.0, 'POLAW': 0.0, 'ABSDED': 0.0, 'MCDED': 0.0, 'PPH21': 0.0, 'JHTDED': 0.0,
                    'GROSS': 0.0, 'NET': 0.0
                }

                for line_data in result_lines:
                    code = line_data['code']
                    if code in amounts:
                        amounts[code] += float(line_data['amount']) or 0.0

                values = [
                    employee.name or '', batch_name, date_from, date_to, ptkp,
                    amounts['BASIC'], amounts['HRA'], amounts['STALW'], amounts['OVT'], amounts['BPSL'],
                    amounts['MALLSITE'], amounts['STALLSITE'], amounts['Travel'], amounts['Meal'],
                    amounts['JHTALW'], amounts['BPJSALW'], amounts['MSCB'], amounts['POLAW'],
                    amounts['ABSDED'], amounts['MCDED'], amounts['PPH21'], amounts['JHTDED'],
                    amounts['GROSS'], amounts['NET'], bank_num
                ]

                for col, val in enumerate(values):
                    fmt = rupiah_format if isinstance(val, (int, float)) else align
                    sheet.write(no, col, val, fmt)

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())