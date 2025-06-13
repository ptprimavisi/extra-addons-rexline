from odoo import fields, models, api
from odoo.exceptions import UserError


class ManpowerRequest(models.Model):
    _name = 'manpower.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    project_name = fields.Char()
    project_location = fields.Char()
    date_request = fields.Date(default=lambda self: fields.Datetime.today())
    date_requirement = fields.Date()
    manpower_ids = fields.One2many('manpower.request.line', 'request_id')
    is_hr = fields.Boolean(compute="_compute_is_hr")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Process'),
        ('done', 'Done')
    ], default='draft')
    # user_domain = fields.Char(compute="_user_domain", search="_search_domain")
    #
    # def _user_domain(self):
    #     uid = self.env.uid
    #     self.user_domain = self.env['res.users'].search([('id', '=', uid)])
    #
    # def _search_domain(self, operator, value):
    #     uid = self.env.uid
    #     uid = self.env.uid
    #     print(uid)
    #     if self.env.user.has_group('ga_custom.ga_custom_groups') or uid in [1, 2]:
    #         domain = [("id", '!=', False)]
    #     else:
    #         employee = self.env['hr.employee'].search([('user_id', '=', int(uid))])
    #         domain = [("employee_id", '=', int(employee.id))]
    #     return domain

    def _compute_is_hr(self):
        for line in self:
            line.is_hr = False
            if self.env.user.has_group('sale_custome.hr_ga_custom_group') or self.env.user.has_group('ga_custom.ga_custom_groups'):
                line.is_hr = True

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('MNREQ') or '/'
        return super(ManpowerRequest, self).create(vals)

    def action_confirm(self):
        for line in self:
            line.state = 'confirm'

    def action_mark_done(self):
        for line in self:
            line.state = 'done'

    def action_reset(self):
        for line in self:
            line.state = 'draft'


class ManpowerRequestLine(models.Model):
    _name = 'manpower.request.line'

    division_id = fields.Many2one('manpower.division')
    position_id = fields.Many2one('manpower.category')
    required_qty = fields.Float()
    hr_feedback = fields.Char()
    replacement = fields.Selection([
        ('new', 'New Manpower'),
        ('replacement', 'Replacement'),
    ], default='new')
    year_required = fields.Float()
    day_required = fields.Float()
    existing_required = fields.Float()
    remark = fields.Char()
    request_id = fields.Many2one('manpower.request')
    is_hr = fields.Boolean(related="request_id.is_hr")
    state = fields.Selection([
        ('process', 'On Process'),
        ('done', 'Done'),
    ], default='process')


class ManpowerCategory(models.Model):
    _name = 'manpower.category'

    name = fields.Char()


class ManpowerDevision(models.Model):
    _name = 'manpower.division'

    name = fields.Char()
