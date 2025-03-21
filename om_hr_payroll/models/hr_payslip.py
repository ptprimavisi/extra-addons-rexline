# -*- coding:utf-8 -*-

import babel
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
                                help='Defines the rules that have to be applied to this payslip, accordingly '
                                     'to the contract chosen. If you let empty the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules applied will be all the rules set on the '
                                     'structure of all contracts of the employee valid for the chosen period')
    name = fields.Char(string='Payslip Name')
    number = fields.Char(string='Reference', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't) and 5 exist ('confirm' seems to have existed)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines')
    company_id = fields.Many2one(
        'res.company', string='Company', copy=False,
        default=lambda self: self.env.company
    )
    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days', 'payslip_id',
        string='Payslip Worked Days', copy=True
    )
    input_line_ids = fields.One2many(
        'hr.payslip.input', 'payslip_id',
        string='Payslip Inputs', copy=True
    )
    paid = fields.Boolean(string='Made Payment Order ? ', copy=False)
    note = fields.Text(string='Internal Note')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    details_by_salary_rule_category = fields.One2many('hr.payslip.line',
                                                      compute='_compute_details_by_salary_rule_category',
                                                      string='Details by Salary Rule Category')
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', copy=False)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslip Computation Details")

    def _compute_details_by_salary_rule_category(self):
        for payslip in self:
            payslip.details_by_salary_rule_category = payslip.mapped('line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        self.compute_sheet()
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        return self.write({'state': 'cancel'})

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        form_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_form', False)
        tree_view_ref = self.env.ref('om_om_hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': (_("Refund Payslip")),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(tree_view_ref and tree_view_ref.id or False, 'tree'),
                      (form_view_ref and form_view_ref.id or False, 'form')],
            'context': {}
        }

    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = self.env.ref('om_hr_payroll.mail_template_payslip').id
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def check_done(self):
        return True

    def unlink(self):
        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def get_percentage(self, gaji_bruto, kategory):
        if kategory == 'a':
            pph = 0
            if gaji_bruto <= 5400000:
                pph = 0
            elif 5400000 < gaji_bruto <= 5650000:
                pph = 0.0025
            elif 5650000 < gaji_bruto <= 5950000:
                pph = 0.005
            elif 5950000 < gaji_bruto <= 6300000:
                pph = 0.0075
            elif 6300000 < gaji_bruto <= 6750000:
                pph = 0.01
            elif 6750000 < gaji_bruto <= 7500000:
                pph = 0.0125
            elif 7500000 < gaji_bruto <= 8550000:
                pph = 0.015
            elif 8550000 < gaji_bruto <= 9650000:
                pph = 0.0175
            elif 9650000 < gaji_bruto <= 10050000:
                pph = 0.02
            elif 10050000 < gaji_bruto <= 10350000:
                pph = 0.0225
            elif 10350000 < gaji_bruto <= 10700000:
                pph = 0.025
            elif 10700000 < gaji_bruto <= 11050000:
                pph = 0.03
            elif 11050000 < gaji_bruto <= 11600000:
                pph = 0.035
            elif 11600000 < gaji_bruto <= 12500000:
                pph = 0.04
            elif 12500000 < gaji_bruto <= 13750000:
                pph = 0.05
            elif 13750000 < gaji_bruto <= 15100000:
                pph = 0.06
            elif 15100000 < gaji_bruto <= 16950000:
                pph = 0.07
            elif 16950000 < gaji_bruto <= 19750000:
                pph = 0.08
            elif 19750000 < gaji_bruto <= 24150000:
                pph = 0.09
            elif 24150000 < gaji_bruto <= 26450000:
                pph = 0.1
            elif 26450000 < gaji_bruto <= 28000000:
                pph = 0.11
            elif 28000000 < gaji_bruto <= 30050000:
                pph = 0.12
            elif 30050000 < gaji_bruto <= 32400000:
                pph = 0.13
            elif 32400000 < gaji_bruto <= 35400000:
                pph = 0.14
            elif 35400000 < gaji_bruto <= 39100000:
                pph = 0.15
            elif 39100000 < gaji_bruto <= 43850000:
                pph = 0.16
            elif 43850000 < gaji_bruto <= 47800000:
                pph = 0.17
            elif 47800000 < gaji_bruto <= 51400000:
                pph = 0.18
            elif 51400000 < gaji_bruto <= 56300000:
                pph = 0.19
            elif 56300000 < gaji_bruto <= 62200000:
                pph = 0.2
            elif 62200000 < gaji_bruto <= 68600000:
                pph = 0.21
            elif 68600000 < gaji_bruto <= 77500000:
                pph = 0.22
            elif 77500000 < gaji_bruto <= 89000000:
                pph = 0.23
            elif 89000000 < gaji_bruto <= 103000000:
                pph = 0.24
            elif 103000000 < gaji_bruto <= 125000000:
                pph = 0.25
            elif 125000000 < gaji_bruto <= 157000000:
                pph = 0.26
            elif 157000000 < gaji_bruto <= 206000000:
                pph = 0.27
            elif 206000000 < gaji_bruto <= 337000000:
                pph = 0.28
            elif 337000000 < gaji_bruto <= 454000000:
                pph = 0.29
            elif 454000000 < gaji_bruto <= 550000000:
                pph = 0.3
            elif 550000000 < gaji_bruto <= 695000000:
                pph = 0.31
            elif 695000000 < gaji_bruto <= 910000000:
                pph = 0.32
            elif 910000000 < gaji_bruto <= 1400000000:
                pph = 0.33
            elif gaji_bruto > 1400000000:
                pph = 0.34
        elif kategory == 'b':
            if gaji_bruto <= 6200000:
                pph = 0
            elif 6200000 < gaji_bruto <= 6500000:
                pph = 0.0025
            elif 6500000 < gaji_bruto <= 6850000:
                pph = 0.005
            elif 6850000 < gaji_bruto <= 7300000:
                pph = 0.0075
            elif 7300000 < gaji_bruto <= 9200000:
                pph = 0.01
            elif 9200000 < gaji_bruto <= 10750000:
                pph = 0.015
            elif 10750000 < gaji_bruto <= 11250000:
                pph = 0.02
            elif 11250000 < gaji_bruto <= 11600000:
                pph = 0.025
            elif 11600000 < gaji_bruto <= 12600000:
                pph = 0.03
            elif 12600000 < gaji_bruto <= 13600000:
                pph = 0.04
            elif 13600000 < gaji_bruto <= 14950000:
                pph = 0.05
            elif 14950000 < gaji_bruto <= 16400000:
                pph = 0.06
            elif 16400000 < gaji_bruto <= 18450000:
                pph = 0.07
            elif 18450000 < gaji_bruto <= 21850000:
                pph = 0.08
            elif 21850000 < gaji_bruto <= 26000000:
                pph = 0.09
            elif 26000000 < gaji_bruto <= 27700000:
                pph = 0.1
            elif 27700000 < gaji_bruto <= 29350000:
                pph = 0.11
            elif 29350000 < gaji_bruto <= 31450000:
                pph = 0.12
            elif 31450000 < gaji_bruto <= 33950000:
                pph = 0.13
            elif 33950000 < gaji_bruto <= 37100000:
                pph = 0.14
            elif 37100000 < gaji_bruto <= 41100000:
                pph = 0.15
            elif 41100000 < gaji_bruto <= 45800000:
                pph = 0.16
            elif 45800000 < gaji_bruto <= 49500000:
                pph = 0.17
            elif 49500000 < gaji_bruto <= 53800000:
                pph = 0.18
            elif 53800000 < gaji_bruto <= 58500000:
                pph = 0.19
            elif 58500000 < gaji_bruto <= 64000000:
                pph = 0.2
            elif 64000000 < gaji_bruto <= 71000000:
                pph = 0.21
            elif 71000000 < gaji_bruto <= 80000000:
                pph = 0.22
            elif 80000000 < gaji_bruto <= 93000000:
                pph = 0.23
            elif 93000000 < gaji_bruto <= 109000000:
                pph = 0.24
            elif 109000000 < gaji_bruto <= 129000000:
                pph = 0.25
            elif 129000000 < gaji_bruto <= 163000000:
                pph = 0.26
            elif 163000000 < gaji_bruto <= 211000000:
                pph = 0.27
            elif 211000000 < gaji_bruto <= 374000000:
                pph = 0.28
            elif 374000000 < gaji_bruto <= 459000000:
                pph = 0.29
            elif 459000000 < gaji_bruto <= 555000000:
                pph = 0.3
            elif 555000000 < gaji_bruto <= 704000000:
                pph = 0.31
            elif 704000000 < gaji_bruto <= 957000000:
                pph = 0.32
            elif 957000000 < gaji_bruto <= 1405000000:
                pph = 0.33
            elif gaji_bruto > 1405000000:
                pph = 0.34

        elif kategory == 'c':
            if gaji_bruto <= 6600000:
                pph = 0
            elif 6600000 < gaji_bruto <= 6950000:
                pph = 0.0025
            elif 6950000 < gaji_bruto <= 7350000:
                pph = 0.005
            elif 7350000 < gaji_bruto <= 7800000:
                pph = 0.0075
            elif 7800000 < gaji_bruto <= 8850000:
                pph = 0.01
            elif 8850000 < gaji_bruto <= 9800000:
                pph = 0.0125
            elif 9800000 < gaji_bruto <= 10950000:
                pph = 0.015
            elif 10950000 < gaji_bruto <= 11200000:
                pph = 0.0175
            elif 11200000 < gaji_bruto <= 12050000:
                pph = 0.02
            elif 12050000 < gaji_bruto <= 12950000:
                pph = 0.03
            elif 12950000 < gaji_bruto <= 14150000:
                pph = 0.04
            elif 14150000 < gaji_bruto <= 15550000:
                pph = 0.05
            elif 15550000 < gaji_bruto <= 17050000:
                pph = 0.06
            elif 17050000 < gaji_bruto <= 19500000:
                pph = 0.07
            elif 19500000 < gaji_bruto <= 22700000:
                pph = 0.08
            elif 22700000 < gaji_bruto <= 26600000:
                pph = 0.09
            elif 26600000 < gaji_bruto <= 28100000:
                pph = 0.1
            elif 28100000 < gaji_bruto <= 30100000:
                pph = 0.11
            elif 30100000 < gaji_bruto <= 32600000:
                pph = 0.12
            elif 32600000 < gaji_bruto <= 35400000:
                pph = 0.13
            elif 35400000 < gaji_bruto <= 38900000:
                pph = 0.14
            elif 38900000 < gaji_bruto <= 43000000:
                pph = 0.15
            elif 43000000 < gaji_bruto <= 47400000:
                pph = 0.16
            elif 47400000 < gaji_bruto <= 51200000:
                pph = 0.17
            elif 51200000 < gaji_bruto <= 55800000:
                pph = 0.18
            elif 55800000 < gaji_bruto <= 60400000:
                pph = 0.19
            elif 60400000 < gaji_bruto <= 66700000:
                pph = 0.2
            elif 66700000 < gaji_bruto <= 74500000:
                pph = 0.21
            elif 74500000 < gaji_bruto <= 83200000:
                pph = 0.22
            elif 83200000 < gaji_bruto <= 95000000:
                pph = 0.23
            elif 95000000 < gaji_bruto <= 110000000:
                pph = 0.24
            elif 110000000 < gaji_bruto <= 134000000:
                pph = 0.25
            elif 134000000 < gaji_bruto <= 169000000:
                pph = 0.26
            elif 169000000 < gaji_bruto <= 221000000:
                pph = 0.27
            elif 221000000 < gaji_bruto <= 390000000:
                pph = 0.28
            elif 390000000 < gaji_bruto <= 463000000:
                pph = 0.29
            elif 463000000 < gaji_bruto <= 561000000:
                pph = 0.3
            elif 561000000 < gaji_bruto <= 709000000:
                pph = 0.31
            elif 709000000 < gaji_bruto <= 965000000:
                pph = 0.32
            elif 965000000 < gaji_bruto <= 1419000000:
                pph = 0.33
            elif gaji_bruto > 1419000000:
                pph = 0.34

        return pph

    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip_line = self.env['hr.payslip.line'].search(
                [('slip_id', '=', payslip.id), ('salary_rule_id.is_manual', '!=', True)])
            payslip_line.unlink()

            # payslip.line_ids.unlink()
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
            if not contract_ids:
                raise ValidationError(
                    _("No running contract found for the employee: %s or no contract in the given period" % payslip.employee_id.name))
            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
            # print(lines)
            # overtime = self.env['hr.salary.rule']
            payslip.write({'line_ids': lines, 'number': number})
            contract_sebelum = self.env['hr.contract'].search(
                [('id', '!=', payslip.contract_id.id), ('employee_id', '=', payslip.employee_id.id),
                 ('date_end', '>=', payslip.date_from), ('date_end', '<', payslip.date_to), ('state', '!=', 'cancel')])
            total_hari_sebelum = 0
            total_hari_sesudah = 0
            if contract_sebelum and payslip.contract_id:
                date_start = datetime.strptime(str(payslip.date_from), '%Y-%m-%d')
                date_end = datetime.strptime(str(contract_sebelum.date_end), '%Y-%m-%d')
                current_date = date_start
                while current_date <= date_end:
                    # print(f"Current Date: {current_date.strftime('%Y-%m-%d')}")
                    # Tambahkan logika lain di sini, misalnya cek data atau melakukan operasi lain
                    total_hari_sebelum += 1
                    current_date += timedelta(days=1)  # Tambah 1 hari
                gj_pkwt = contract_sebelum.wage
                total_gaji_sebelum = total_hari_sebelum / 30 * gj_pkwt
                hari_sesudah = 30 - total_hari_sebelum
                total_hari_sesudah += hari_sesudah
                gaji_pkwt_sesudah = payslip.contract_id.wage
                total_gaji_sesudah = total_hari_sesudah / 30 * gaji_pkwt_sesudah
                final_gaji = total_gaji_sebelum + total_gaji_sesudah
                basic = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('code', '=', 'BASIC')])
                gross = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('code', '=', 'GROSS')])
                net = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('code', '=', 'NET')])
                gross.write({'amount': gross.amount - basic.amount})
                gross.write({'amount': gross.amount + final_gaji})
                net.write({'amount': net.amount - basic.amount})
                net.write({'amount': net.amount + final_gaji})
                basic.write({'amount': final_gaji})

                # for forlines in payslip.line_ids:
                #     if forlines.code == 'BASIC':
                #         forlines.amount = final_gaji

                # slipline = self.env['hr.payslip.line'].browse(int(forlines.category_id.id))
                # if slipline:
                #     raise UserError(slipline.amount)
                #     slipline.write({'amount': final_gaji})
                # raise UserError(total_gaji_sebelum)
                # date_start_cont = datetime.strptime(str(contract_sebelum.date_end), '%Y-%m-%d')
                # date_start_sesudah = date_start_cont + timedelta(days=1)
                # date_end_sesudah = datetime.strptime(str(payslip.date_to), '%Y-%m-%d')

                # while date_start_sesudah <= date_end_sesudah:
                #     total_hari_sesudah += 1
                #     date_start_sesudah += timedelta(days=1)

            # raise UserError(total_hari_sesudah)
            if payslip.line_ids:
                for liness in payslip.line_ids:
                    if liness.salary_rule_id.is_manual and liness.salary_rule_id.amount_select == 'fix' and liness.salary_rule_id.amount_fix == 0:
                        # raise UserError(lines.amount)
                        if liness.category_id.id == 2:  # allowance
                            gross = self.env['hr.payslip.line'].search(
                                [('slip_id', '=', int(payslip.id)), ('category_id', '=', 3)])
                            gross.write({'amount': gross.amount + liness.amount})
                            # gross.write({'amount': gross.amount + liness.amount})
                            gaji_net = self.env['hr.payslip.line'].search(
                                [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                            gaji_net.write({'amount': gaji_net.amount + liness.amount})

                        elif liness.category_id.id == 4:  # deduction
                            gaji_net = self.env['hr.payslip.line'].search(
                                [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                            gaji_net.write({'amount': gaji_net.amount - liness.amount})
            for slip_line in payslip.line_ids:
                if slip_line.salary_rule_id.code == 'MALLSITE':
                    date_from = payslip.date_from  # Format: YYYY-MM-DD
                    date_to = payslip.date_to
                    jumlah_surat = 0
                    # Mengubah string menjadi objek datetime
                    date_from_obj = datetime.strptime(str(date_from), "%Y-%m-%d")
                    date_to_obj = datetime.strptime(str(date_to), "%Y-%m-%d")

                    # Iterasi per tanggal
                    nominal = 0
                    current_date = date_from_obj
                    while current_date <= date_to_obj:
                        today = current_date.strftime("%Y-%m-%d")  # Format tanggal ke string (opsional)
                        surat_tugas = self.env['hr.surat.tugas.line'].search(
                            [('employee_id', '=', payslip.employee_id.id),
                             ('surat_id.state', '=', 'done'),
                             ('surat_id.date_from', '<=', today),  # date_from <= today
                             ('surat_id.date_to', '>=', today)  # date_to >= today
                             ])
                        # raise UserError(today)
                        if surat_tugas:
                            nominal = surat_tugas.surat_id.meal_allowance
                            jumlah_surat += 1
                        current_date += timedelta(days=1)  # Menambah 1 hari
                    meal_allowance = nominal * jumlah_surat
                    gaji_net = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                    gaji_gross = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['GROSS'])])
                    slip_line.quantity = jumlah_surat
                    slip_line.amount = nominal
                    gaji_net.amount = gaji_net.amount + meal_allowance
                    gaji_gross.amount = gaji_gross.amount + meal_allowance

                    # raise UserError(meal_allowance)

                # absence deduction
                if slip_line.salary_rule_id.code == 'ABSDED':
                    date_from_obj = datetime.strptime(str(payslip.date_from), "%Y-%m-%d")
                    date_to_obj = datetime.strptime(str(payslip.date_to), "%Y-%m-%d")
                    current_date = date_from_obj
                    abs_ded_amount = 0
                    jumlah_tdk_absence = 0
                    if payslip.contract_id.schedule_type_id:
                        while current_date <= date_to_obj:
                            today = current_date.strftime("%Y-%m-%d")
                            hari = current_date.strftime('%A')
                            if payslip.contract_id.schedule_type_id.hari_id:
                                master_hari = self.env['master.hari'].search([('id','in',payslip.contract_id.schedule_type_id.hari_id.ids),
                                                                              ('name','=',str(hari))])
                                if master_hari:
                                    print(f'Available tgl {today} -- Available Hari {master_hari.name}')
                                    attendance = self.env['hr.attendance'].search([('employee_id', '=', payslip.employee_id.id),
                                        ('check_in', '>=',current_date.strftime('%Y-%m-%d 00:00:00')),
                                        # Awal hari
                                        ('check_in', '<=', current_date.strftime('%Y-%m-%d 23:59:59'))])

                                    # sakit
                                    timeoff = self.env['hr.leave'].search([('employee_id', '=', payslip.employee_id.id),
                                                                           ('request_date_from', '>=',
                                                                            current_date.strftime('%Y-%m-%d 00:00:00')),
                                                                           # Awal hari
                                                                           ('request_date_from', '<=',
                                                                            current_date.strftime('%Y-%m-%d 23:59:59'))
                                                                           ])

                                    roster = self.env['hr.roster'].search([('employee_id', '=', payslip.employee_id.id),
                                                                           ('state', '=', 'confirm'),
                                                                           ('date_from', '<=', today),
                                                                           ('date_to', '>=', today)
                                                                           ])
                                    surat_tugas = self.env['hr.surat.tugas.line'].search(
                                        [('employee_id', '=', payslip.employee_id.id),
                                         ('surat_id.state', '=', 'done'),
                                         ('surat_id.date_from', '<=', today),  # date_from <= today
                                         ('surat_id.date_to', '>=', today)  # date_to >= today
                                         ])
                                    if not attendance:
                                        if timeoff and not roster: #cuti
                                            nonsite = payslip.contract_id.meal_allowance + payslip.contract_id.transport_allowance
                                            final_nonsite = nonsite / 30
                                            abs_ded_amount += final_nonsite
                                            # raise UserError(today)
                                            if surat_tugas:
                                                abs_ded_amount += surat_tugas.surat_id.site_allowance
                                        if roster and not timeoff:
                                            if surat_tugas:
                                                sites_alw = surat_tugas.surat_id.site_allowance + surat_tugas.surat_id.meal_allowance
                                                abs_ded_amount += sites_alw
                                        if not roster and not timeoff:
                                            thp = payslip.contract_id.wage + payslip.contract_id.position_allowance + payslip.contract_id.medical_allowance + payslip.contract_id.hra + payslip.contract_id.meal_allowance + payslip.contract_id.transport_allowance
                                            total_ded = thp / 30
                                            abs_ded_amount += total_ded
                                        jumlah_tdk_absence += 1

                            current_date += timedelta(days=1)
                        absence_deduction = self.env['hr.payslip.line'].search(
                            [('slip_id', '=', int(payslip.id)), ('code', 'in', ['ABSDED'])])
                        if absence_deduction and not absence_deduction.is_manual:
                            absence_deduction.amount = abs_ded_amount
                        gaji_net = self.env['hr.payslip.line'].search(
                            [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                        gaji_net.amount = gaji_net.amount - abs_ded_amount
                        print(f'{int(abs_ded_amount)} -- {jumlah_tdk_absence}')

                if slip_line.salary_rule_id.code == 'STALLSITE':
                    date_from = payslip.date_from  # Format: YYYY-MM-DD
                    date_to = payslip.date_to
                    jumlah_surat = 0
                    # Mengubah string menjadi objek datetime
                    date_from_obj = datetime.strptime(str(date_from), "%Y-%m-%d")
                    date_to_obj = datetime.strptime(str(date_to), "%Y-%m-%d")

                    # Iterasi per tanggal
                    nominal = 0
                    mealall = 0
                    current_date = date_from_obj
                    abs_ded = 0
                    while current_date <= date_to_obj:
                        today = current_date.strftime("%Y-%m-%d")  # Format tanggal ke string (opsional)
                        surat_tugas = self.env['hr.surat.tugas.line'].search(
                            [('employee_id', '=', payslip.employee_id.id),
                             ('surat_id.state', '=', 'done'),
                             ('surat_id.date_from', '<=', today),  # date_from <= today
                             ('surat_id.date_to', '>=', today)  # date_to >= today
                             ])
                        # raise UserError(today)
                        if surat_tugas:
                            nominal = surat_tugas.surat_id.site_allowance
                            mealall = surat_tugas.surat_id.meal_allowance
                            jumlah_surat += 1
                            # attendance = self.env['hr.attendance'].search([('employee_id', '=', payslip.employee_id.id),
                            #                                                ('check_in', '>=',
                            #                                                 current_date.strftime('%Y-%m-%d 00:00:00')),
                            #                                                # Awal hari
                            #                                                ('check_in', '<=', current_date.strftime(
                            #                                                    '%Y-%m-%d 23:59:59'))])
                            # if not attendance and not slip_line.salary_rule_id.is_manual:
                            #     timeoff = self.env['hr.leave'].search([('employee_id', '=', payslip.employee_id.id),
                            #                                            ('request_date_from', '>=',
                            #                                             current_date.strftime('%Y-%m-%d 00:00:00')),# Awal hari
                            #                                            ('request_date_from', '<=',
                            #                                             current_date.strftime('%Y-%m-%d 23:59:59'))
                            #                                            ])
                            #     roster = self.env['hr.roster'].search([('employee_id','=',payslip.employee_id.id),
                            #                                            ('state','=','confirm'),
                            #                                            ('date_from', '<=', today),
                            #                                            ('date_to', '>=', today)
                            #                                            ])
                            #     if timeoff and not roster:
                            #         nonsite = payslip.contract_id.meal_allowance + payslip.contract_id.transport_allowance
                            #         final_nonsite = nonsite / 30
                            #         abs_ded += final_nonsite
                            #         abs_ded += nominal
                            #     if roster and not timeoff:
                            #         site_al = nominal + mealall
                            #         abs_ded += site_al
                            #     if not timeoff and not roster:
                            #         nonsite = payslip.contract_id.meal_allowance + payslip.contract_id.transport_allowance
                            #         final_nonsite = nonsite / 30
                            #         site_al = nominal + mealall
                            #         final = final_nonsite + site_al
                            #         abs_ded += final
                            # raise UserError(timeoff)

                        current_date += timedelta(days=1)  # Menambah 1 hari
                    site_allowance = nominal * jumlah_surat
                    gaji_net = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                    gaji_gross = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['GROSS'])])
                    slip_line.quantity = jumlah_surat
                    slip_line.amount = nominal
                    gaji_net.amount = gaji_net.amount + site_allowance
                    gaji_gross.amount = gaji_gross.amount + site_allowance
                    # absence_deduction = self.env['hr.payslip.line'].search(
                    #     [('slip_id', '=', int(payslip.id)), ('code', 'in', ['ABSDED'])])
                    # if absence_deduction and not absence_deduction.is_manual:
                    #     absence_deduction.amount = abs_ded
                    # gaji_net.amount = gaji_net.amount - abs_ded

                if slip_line.salary_rule_id.code == 'PARTIME':
                    pt_amount = 0
                    pt_quantity = 0
                    date_from = payslip.date_from  # Format: YYYY-MM-DD
                    date_to = payslip.date_to

                    # Mengubah string menjadi objek datetime
                    date_from_obj = datetime.strptime(str(date_from), "%Y-%m-%d")
                    date_to_obj = datetime.strptime(str(date_to), "%Y-%m-%d")

                    # Iterasi per tanggal
                    current_date = date_from_obj
                    while current_date <= date_to_obj:
                        today = current_date.strftime("%Y-%m-%d")  # Format tanggal ke string (opsional)
                        daily_report = self.env['man.power.line'].search(
                            [('employee_id', '=', payslip.employee_id.id), ('report_id.date', '=', str(today))],
                            limit=1)
                        # raise UserError(today)
                        print(today)
                        if daily_report:
                            pt_quantity += 1
                        current_date += timedelta(days=1)  # Menambah 1 hari
                    # raise UserError(pt_quantity)
                    slip_line.quantity = pt_quantity
                    gaji_net = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                    pengurang = gaji_net.amount - slip_line.amount
                    gaji_net.amount = pengurang
                    gaji_net.amount = gaji_net.amount + slip_line.total

                if slip_line.salary_rule_id.code == 'OVT':
                    sk_amount = 0
                    sk = self.env['surat.kerja.line'].search(
                        [('employee_id', '=', payslip.employee_id.id), ('sk_id.type', '=', 'overtime'),
                         ('state', '=', 'approved'), ('date_from', '>=', payslip.date_from),
                         ('date_from', '<=', payslip.date_to)])
                    for sk_lines in sk:
                        date_string = str(sk_lines.date_from).split(' ')[0]
                        self._cr.execute(
                            "SELECT * FROM hr_attendance WHERE employee_id = '" + str(
                                payslip.employee_id.id) + "' and date(check_in) = '" + str(
                                date_string) + "'")
                        for atts in self._cr.dictfetchall():
                            if atts:
                                tanggal_obj = datetime.strptime(str(date_string), '%Y-%m-%d')
                                # raise UserError(tanggal_obj.strftime('%A'))
                                basic_salary = self.env['hr.payslip.line'].search(
                                    [('slip_id', '=', int(payslip.id)), ('category_id', '=', 1)])
                                # raise UserError(date_string)
                                if tanggal_obj.weekday() == 6:
                                    work_hour = sk_lines.work_hour_approve
                                    if sk_lines.work_hour_approve <= 8:
                                        amount_ovt = 1.5 * basic_salary.amount / 173
                                        sk_amount += amount_ovt * work_hour
                                    else:
                                        sisa_waktu = work_hour - 8
                                        amount_before = 1.5 * basic_salary.amount / 173 * 8
                                        amount_after = basic_salary.amount / 173 * sisa_waktu
                                        sk_amount += amount_before + amount_after

                                else:
                                    amount_ovt = basic_salary.amount / 173
                                    work_hour = sk_lines.work_hour_approve
                                    if sk_lines.work_hour_approve > 4:
                                        work_hour = 4
                                    sk_amount += amount_ovt * work_hour

                    gross = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('category_id', '=', 3)])
                    gross.write({'amount': gross.amount + sk_amount})
                    gaji_net = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                    gaji_net.write({'amount': gaji_net.amount + sk_amount})
                    slip_line.amount = sk_amount

            pph = self.env['hr.payslip.line'].search(
                [('slip_id', '=', int(payslip.id)), ('code', 'in', ['PPH21'])])
            pph_alw = self.env['hr.payslip.line'].search(
                [('slip_id', '=', int(payslip.id)), ('code', 'in', ['TAXALW'])])
            basic = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('category_id', '=', 1)])
            alw = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('category_id', '=', 2)])
            ded = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('category_id', '=', 4)])
            gross = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('category_id', '=', 3)])
            date_to = str(payslip.date_to).split("-")[1]
            if date_to != '12':
                basic_amount = 0.0
                alw_amount = 0.0
                gaji_bruto = 0
                for b in basic:
                    basic_amount += b.amount
                    gaji_bruto += b.amount

                for a in alw:
                    alw_amount += a.amount
                    gaji_bruto += a.amount

                if payslip.contract_id.ptkp_id:
                    if payslip.contract_id.ptkp_id.kategori_pph == 'a':
                        persentase = self.get_percentage(gaji_bruto, 'a')
                    elif payslip.contract_id.pph_kategori.kategori == 'b':
                        persentase = self.get_percentage(gaji_bruto, 'b')
                    elif payslip.contract_id.pph_kategori.kategori == 'b':
                        persentase = self.get_percentage(gaji_bruto, 'c')
                    amount = (persentase) * (gaji_bruto)

                    if amount > 1000000:
                        amount = 1000000
                        new_amount = (persentase) * (gaji_bruto)
                        final_amount = new_amount - 1000000
                        # raise UserError(final_amount)
                        pph.write({'amount': final_amount})
                        gaji_net = self.env['hr.payslip.line'].search(
                            [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                        gaji_net.write({'amount': gaji_net.amount - final_amount})
                    if pph_alw:
                        pph_alw.write({'amount': amount})


            else:
                basic_amount = 0.0
                alw_amount = 0.0
                deb_amount = 0.0
                pph_amount = 0.0
                tanggal = datetime.strptime(str(payslip.date_from), '%Y-%m-%d')

                # Mendapatkan tanggal awal dan akhir tahun
                tanggal_awal_tahun = tanggal.replace(month=1, day=1)
                tanggal_akhir_tahun = tanggal.replace(month=12, day=31)
                self._cr.execute(
                    "SELECT * FROM hr_payslip WHERE date_from >= '" + str(
                        tanggal_awal_tahun) + "' and date_to <= '" + str(
                        tanggal_akhir_tahun) + "' and employee_id = " + str(
                        payslip.employee_id.id))
                for line in self._cr.dictfetchall():
                    pphs = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(line['id'])), ('code', 'in', ['PPH21'])])
                    basic = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(line['id'])), ('category_id', '=', 1)])
                    alw = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(line['id'])), ('category_id', '=', 2)])
                    deb = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(line['id'])), ('category_id', '=', 4), ('code', '!=', 'PPH21')])

                    for b in basic:
                        basic_amount += b.amount

                    for a in alw:
                        alw_amount += a.amount

                    for c in deb:
                        deb_amount += c.amount

                    for d in pphs:
                        pph_amount += d.amount
                basic_amount += self.env['hr.payslip.line'].search(
                    [('slip_id', '=', int(payslip.id)), ('category_id', '=', 1)]).amount or 0.0
                for alw_des in self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('category_id', '=', 2)]):
                    alw_amount += alw_des.amount
                for deb_des in self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('category_id', '=', 4), ('code', '!=', 'PPH21')]):
                    deb_amount += deb_des.amount

                if payslip.contract_id.ptkp_id:
                    gapok = basic_amount + alw_amount
                    gajiPokok = gapok
                    netto = gajiPokok - ((deb_amount))
                    penghasilanKenaPajak = netto - payslip.contract_id.ptkp_id.nominal

                    # pph = self.env['hr.payslip.line'].search([('slip_id', '=', int(payslip.id)), ('code', 'in', ['PPH_21_BARU'])])
                    # pph.write({'amount': penghasilanKenaPajak})
                    if penghasilanKenaPajak < 60000000:
                        amount = (5 / 100) * penghasilanKenaPajak
                        penghasilanKenaPajak -= penghasilanKenaPajak
                    elif penghasilanKenaPajak >= 60000000:
                        amount = (5 / 100) * 60000000
                        penghasilanKenaPajak -= 60000000
                    if penghasilanKenaPajak < 250000000:
                        amount += (15 / 100) * penghasilanKenaPajak
                        penghasilanKenaPajak -= penghasilanKenaPajak
                    elif penghasilanKenaPajak >= 250000000:
                        amount += (15 / 100) * 250000000
                        penghasilanKenaPajak -= 250000000
                    if penghasilanKenaPajak < 500000000:
                        amount += (25 / 100) * penghasilanKenaPajak
                        penghasilanKenaPajak -= penghasilanKenaPajak
                    elif penghasilanKenaPajak >= 500000000:
                        amount += (25 / 100) * 500000000
                    if penghasilanKenaPajak != 0.0:
                        while True:
                            if penghasilanKenaPajak < 500000000:
                                amount += (30 / 100) * penghasilanKenaPajak
                                penghasilanKenaPajak -= penghasilanKenaPajak
                            else:
                                amount += (30 / 100) * 500000000
                                penghasilanKenaPajak -= 500000000

                            if penghasilanKenaPajak <= 0.0:
                                break

                    result = amount - (pph_amount)
                    pph = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(payslip.id)), ('code', 'in', ['PPH21'])])
                    pphs_alw = self.env['hr.payslip.line'].search(
                        [('slip_id', '=', int(line['id'])), ('code', 'in', ['TAXALW'])])

                    if result > 1000000:
                        result = 1000000
                        new_res = amount - (pph_amount)
                        final_result = new_res - 1000000
                        pph.write({'amount': final_result})
                        gaji_net = self.env['hr.payslip.line'].search(
                            [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                        gaji_net.write({'amount': gaji_net.amount - final_result})
                    if pphs_alw:
                        pphs_alw.write({'amount': result})

        return True

    def action_existing(self):
        for payslip in self:
            if payslip.line_ids:
                for lines in payslip.line_ids:

                    if lines.salary_rule_id.is_manual and lines.salary_rule_id.amount_select == 'fix' and lines.salary_rule_id.amount_fix == 0:
                        # raise UserError(lines.amount)
                        if lines.category_id.id == 2:  # allowance
                            if lines.quantity != 0 and lines.amount != 0:
                                lines.amount = lines.amount
                                gross = self.env['hr.payslip.line'].search(
                                    [('slip_id', '=', int(payslip.id)), ('category_id', '=', 3)])
                                original_amount = gross.read(['amount'])[0]['amount']
                                # raise UserError(original_amount)

                                if gross.amount < gross.amount + lines.amount:
                                    gross.write({'amount': gross.amount + lines.amount})
                                elif gross.amount >= gross.amount + lines.amount:
                                    gross.write({'amount': gross.amount - lines.amount})
                                    # gross.write({'amount': gross.amount + lines.amount})
                                gaji_net = self.env['hr.payslip.line'].search(
                                    [('slip_id', '=', int(payslip.id)), ('code', 'in', ['NET'])])
                                if gaji_net.amount < gaji_net.amount + lines.amount:
                                    gaji_net.write({'amount': gaji_net.amount + lines.amount})
                                elif gaji_net.amount >= gaji_net.amount + lines.amount:
                                    gaji_net.write({'amount': gaji_net.amount - lines.amount})
                                    # gaji_net.write({'amount': gaji_net.amount + lines.amount})
                        elif lines.category_id.id == 4:  # deduction
                            pass

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to,
                                                                   calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] -= hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] -= hours / work_hours

            # compute worked days
            work_data = contract.employee_id._get_work_days_data(
                day_from,
                day_to,
                calendar=contract.resource_calendar_id,
                compute_leaves=False,
            )
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                res += [input_data]
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and \
                                                          localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                    (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    if not any(rule.id == items.salary_rule_id.id for items in payslip.line_ids):
                        # compute the amount of the rule
                        amount, qty, rate = rule._compute_rule(localdict)
                        # check if there is already a rule computed with that code
                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                        # set/overwrite the amount computed for this rule in the localdict
                        tot_rule = contract.company_id.currency_id.round(amount * qty * rate / 100.0)
                        localdict[rule.code] = tot_rule
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                        # create/overwrite the rule in the temporary results
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                        }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    # YTI TODO To rename. This method is not really an onchange, as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # defaults
        res = {
            'value': {
                'line_ids': [],
                # delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                # delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                # 'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        self.ensure_one()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []

        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (
            employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
        self.company_id = employee.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        if contracts:
            worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
            worked_days_lines = self.worked_days_line_ids.browse([])
            for r in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(r)
            self.worked_days_line_ids = worked_days_lines

            input_line_ids = self.get_inputs(contracts, date_from, date_to)
            input_lines = self.input_line_ids.browse([])
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            self.input_line_ids = input_lines
            return

    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0


class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    rate = fields.Float(string='Rate (%)', default=100.0)
    amount = fields.Float()
    quantity = fields.Float(default=1.0)
    total = fields.Float(compute='_compute_total', string='Total')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('You must set a contract to create a payslip line.'))
        return super(HrPayslipLine, self).create(vals_list)


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
                                  help="The contract for which applied this input")


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
                                  help="The contract for which applied this input")


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(
        string='Date From', required=True,
        default=lambda self: fields.Date.to_string(date.today().replace(day=1))
    )
    date_end = fields.Date(
        string='Date To', required=True,
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date())
    )
    credit_note = fields.Boolean(
        string='Credit Note',
        help="If its checked, indicates that all payslips generated from here are refund payslips."
    )

    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        return self.write({'state': 'close'})

    def done_payslip_run(self):
        for line in self.slip_ids:
            line.action_payslip_done()
        return self.write({'state': 'done'})

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise ValidationError(_('You Cannot Delete Done Payslips Batches'))
        return super(HrPayslipRun, self).unlink()
