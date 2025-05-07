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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('MNREQ') or '/'
        return super(ManpowerRequest, self).create(vals)

    def action_confirm(self):
        for line in self:
            line.state = 'done'


class ManpowerRequestLine(models.Model):
    _name = 'manpower.request.line'

    position_id = fields.Many2one('manpower.category')
    required_qty = fields.Float()
    replacement = fields.Char()
    year_required = fields.Float()
    day_required = fields.Float()
    existing_required = fields.Float()
    remark = fields.Char()
    request_id = fields.Many2one('manpower.request')


class ManpowerCategory(models.Model):
    _name = 'manpower.category'

    name = fields.Char()
