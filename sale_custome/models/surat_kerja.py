from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime, time
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
        ('partime', 'Partime'),
        ('overtime', 'Overtime')
    ])
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
                if time_str > '21:00:00':
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

    @api.onchange('date_from', 'date_to')
    def onchange_date(self):
        for line in self:
            if line.date_from and line.date_to:
                # to = datetime.strptime(str(line.date_to), "%d-%m-%Y %H:%M:%S")
                # from_ = datetime.strptime(str(line.date_from), "%d-%m-%Y %H:%M:%S")
                time_difference_seconds = (line.date_to - line.date_from).total_seconds()
                # Menghitung selisih jam
                hours_difference = time_difference_seconds / 3600
                line.work_hour = hours_difference
                line.work_hour_approve = hours_difference
