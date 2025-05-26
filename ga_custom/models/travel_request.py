from odoo import fields, models, api
from odoo.exceptions import UserError


class TravelRequest(models.Model):
    _name = 'travel.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
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
        ('done', 'Done')
    ], default='draft')

    def action_confirm(self):
        for line in self:
            line.state = 'done'

    def _compute_is_hr(self):
        for line in self:
            line.is_hr = False
            if self.env.user.has_group('sale_custome.hr_ga_custom_group') or self.env.user.has_group('ga_custom.ga_custom_groups'):
                line.is_hr = True

    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            line.department_id = False
            if line.employee_id.department_id:
                line.department_id = line.employee_id.department_id.id

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('TREQ')
        return super(TravelRequest, self).create(vals)
