from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime, time, timedelta
import pytz
import re


class SuratKerja(models.Model):
    _name = 'surat.kerja'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    progres_id = fields.Many2one('production.report')
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    work_hours = fields.Float()
    description = fields.Text()
    type = fields.Selection([
        ('overtime', 'Overtime')
    ])
    department_id = fields.Many2one('hr.department')
    surat_kerja_line_ids = fields.One2many('surat.kerja.line', 'sk_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm')
    ], default='draft')
    is_night = fields.Boolean(compute="_compute_is_night", store=True)

    @api.depends('date_to')
    def _compute_is_night(self):
        for line in self:
            line.is_night = False
            if line.date_to:
                utc_now = line.date_to
                jakarta_tz = pytz.timezone('Asia/Jakarta')
                jakarta_time = utc_now.astimezone(jakarta_tz)
                jakarta_time = str(jakarta_time).split(' ')[1]

                time_str = jakarta_time.split('+')[0]

                print(time_str)
                # print("Waktu saat ini di Asia/Jakarta:", jakarta_time.strftime('%Y-%m-%d %H:%M:%S'))
                if time_str > '18:00:00':
                    line.is_night = True

    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('SK') or '/'
        return super(SuratKerja, self).create(vals_list)

    def default_get(self, fields_list):
        defaults = super(SuratKerja, self).default_get(fields_list)
        progress_id = self.env.context.get('progres_id', False)
        if progress_id:
            defaults['progres_id'] = progress_id

        return defaults
        # for line in self:

    def action_confirm(self):
        for line in self:
            line.state = 'confirmed'
            line_sk = self.env['surat.kerja.line'].search([('sk_id', '=', int(line.id))])
            for lines in line_sk:
                lines.state = 'approved'

    @api.onchange('date_from', 'date_to')
    def onchange_date(self):
        for line in self:
            if line.date_from and line.date_to:
                # to = datetime.strptime(str(line.date_to), "%d-%m-%Y %H:%M:%S")
                # from_ = datetime.strptime(str(line.date_from), "%d-%m-%Y %H:%M:%S")
                time_difference_seconds = (line.date_to - line.date_from).total_seconds()
                # Menghitung selisih jam
                hours_difference = time_difference_seconds / 3600
                line.work_hours = hours_difference

    # def default_get(self, fields_list):
    #     for line in self:
    #         defaults = super(SuratKerja, self).default_get(fields_list)
    #         # if defaults['date_from'] and defaults['date_to']:
    #         # a = defaults['date_from']
    #         if defaults:
    #             if defaults.get('date_from') and defaults.get('date_to'):
    #                 # time_difference_seconds = (defaults.get('date_to') - defaults.get('date_from')).total_seconds()
    #                 #
    #                 # # Menghitung selisih jam
    #                 # hours_difference = time_difference_seconds / 3600
    #                 defaults['work_hours'] = 8.0
    #
    #         return defaults

    # def _compute_work_hours(self):
    #     for line in self:
    #         time_difference_seconds = (line.date_to - line.date_from).total_seconds()
    #
    #         # Menghitung selisih jam
    #         hours_difference = time_difference_seconds / 3600
    #         return 8

class EmployeeMutationLine(models.Model):
    _name = 'employee.mutation.line'
    _description = 'Employee Mutation Entry'
    _order = 'date_from desc'

    name = fields.Char(string='Nama')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    position = fields.Char(string='Position')
    department_id = fields.Many2one('hr.department', string='Department')
    location_id = fields.Char()
    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade')

class SuratKerjaLine(models.Model):
    _name = 'surat.kerja.line'

    sk_id = fields.Many2one('surat.kerja')
    employee_id = fields.Many2one('hr.employee')
    # employee_id = fields.Many2one('hr.employee')
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    work_hour = fields.Float()
    work_hour_approve = fields.Float()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved')
    ], default='draft')
    rest = fields.Float()

    @api.onchange('date_from', 'date_to', 'rest')
    def onchange_date(self):
        for line in self:
            if line.date_from and line.date_to:
                # to = datetime.strptime(str(line.date_to), "%d-%m-%Y %H:%M:%S")
                # from_ = datetime.strptime(str(line.date_from), "%d-%m-%Y %H:%M:%S")
                time_difference_seconds = (line.date_to - line.date_from).total_seconds()
                # Menghitung selisih jam
                hours_difference = time_difference_seconds / 3600
                final_hour = hours_difference - line.rest
                line.work_hour = final_hour
                line.work_hour_approve = final_hour


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    alert_state = fields.Boolean(compute="_compute_contract", store=True)
    color_field = fields.Char(string='Background color')
    mutation_line_ids = fields.One2many('employee.mutation.line', 'employee_id', string='Mutations')
    npwp = fields.Char('NPWP Number')
    bpjs_number = fields.Char('BPJS Number')

    @api.depends('contract_ids')
    def _compute_contract(self):
        for line in self:

            today = datetime.now()

            # Tanggal 40 hari sebelumnya
            days_before = today + timedelta(days=40)
            # raise UserError(days_before)
            contract = self.env['hr.contract'].search([('id', 'in', line.contract_ids.ids), ('date_end','>',str(days_before))])
            if contract:
                line.alert_state = False
                line.color_field = 'white'
            else:
                line.alert_state = True
                line.color_field = '#fdc6c673'

    def action_create_user(self):
        for line in self:
            department = line.department_id.id
            if department:
                employee = self.env['hr.employee'].search([
                    ('department_id', '=', int(line.department_id.id)),
                    ('user_id', '!=', False),
                    ('user_id.state', '=', 'active')
                ], order='create_date desc', limit=1)
                if not line.user_id:
                    if line.work_email:
                        if employee or employee.user_id:
                            new_user = employee.user_id.copy()

                            # Update field pada user baru
                            new_user.write({
                                'name': line.name,
                                'login': line.work_email,
                            })
                            new_user.partner_id.email = line.work_email

                            # Set user_id di line
                            line.user_id = new_user.id
                        else:
                            new_user = self.env['res.users'].create({
                                'name': line.name,
                                'login': line.work_email,
                            })

                            # Update field pada user baru
                            new_user.write({
                                'name': line.name,
                                'login': line.work_email,
                            })

                            # Set user_id di line
                            new_user.partner_id.email = line.work_email
                            line.user_id = new_user.id

                    else:
                        raise UserError('Work Email is Missing')
                        exit()
                        # print(final)
                        # exit()
                        # line.user_id = int(final.id)
            else:
                raise UserError('Missing department!')




