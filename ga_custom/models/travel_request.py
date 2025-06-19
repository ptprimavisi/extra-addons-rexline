from odoo import fields, models, api
from odoo.exceptions import UserError


class TravelRequest(models.Model):
    _name = 'travel.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
    job_id = fields.Many2one('hr.job', 'Job Position')
    purpose = fields.Char()
    destination = fields.Char()
    so_number = fields.Char()
    request_date = fields.Date(default=lambda self: fields.Datetime.today())
    dest_from = fields.Char()
    dest_to = fields.Char()
    days = fields.Integer()
    tickets = fields.Char()
    hotels = fields.Char()
    other = fields.Char()
    is_hr = fields.Boolean(compute="_compute_is_hr")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('process', 'On Process'),
        ('done', 'Done')
    ], default='draft')
    description = fields.Text()

    transport_type = fields.Selection([
        ('kapal', 'Ship'),
        ('pesawat', 'Flight'),
        ('bus', 'Bus'),
        ('kereta', 'Train'),
        ('mobil', 'Car')
    ])
    tax = fields.Integer('Tax')
    vendor = fields.Char('Vendor')
    payment_method = fields.Selection([
        ('tunai', 'Cash'),
        ('tempo', 'Tempo'),
        ('credit', 'Credit Card')
    ])
    start_travel = fields.Date('Date From')
    end_travel = fields.Date('Date To')
    total_prices = fields.Integer('Total Price')

    def action_confirm(self):
        for line in self:
            line.state = 'process'

    def action_mark_done(self):
        for line in self:
            line.state = 'done'

    def action_reset_to_draft(self):
        for line in self:
            line.state = 'draft'

    def _compute_is_hr(self):
        for line in self:
            line.is_hr = False
            if self.env.user.has_group('sale_custome.hr_ga_custom_group') or self.env.user.has_group(
                    'ga_custom.ga_custom_groups'):
                line.is_hr = True

    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            line.department_id = False
            line.job_id = False
            if line.employee_id.department_id and line.employee_id.job_id:
                line.department_id = line.employee_id.department_id.id
                line.job_id = line.employee_id.job_id
    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('TREQ')
        return super(TravelRequest, self).create(vals)


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    bank_name = fields.Char()
    bank_number = fields.Char()
    account_holder = fields.Char()
