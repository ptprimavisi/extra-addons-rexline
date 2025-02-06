from odoo import fields, models, api
from odoo.exceptions import UserError


class ItRequest(models.Model):
    _name = 'it.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
    date_request = fields.Date(default=lambda self: fields.Datetime.today())
    description = fields.Text()
    justification = fields.Text()
    estimate_price = fields.Float()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    count_requisition = fields.Integer(compute="_count_requisition")

    @api.onchange('employee_id')
    def oc_employee(self):
        for line in self:
            line.department_id = False
            if line.employee_id:
                if line.employee_id.department_id:
                    # raise UserError(line.employee_id.department_id)
                    line.department_id = line.employee_id.department_id.id

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('ITR') or '/'
        return super(ItRequest, self).create(vals)

    def action_confirm(self):
        for line in self:
            line.state = 'done'

    def action_create_mrf(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.requisition",
                "name": "Purchase Requisition",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_it_id': int(line.id),
                    'default_responsible': int(line.user_id.id),
                    'default_employee_id': int(line.employee_id.id),
                    'default_department_id': line.department_id.id,
                    'default_requisition_date': line.date_request,
                    'default_category': 'ut'
                }
            }

    def _count_requisition(self):
        for line in self:
            requisition = self.env['purchase.requisition'].search([('it_id','=',int(line.id))])
            line.count_requisition = 0
            if requisition:
                line.count_requisition = len(requisition)

    def unlink(self):
        for line in self:
            if line.state == 'done':
                raise UserError('This document cannot be deleted, because already done!')
        return super().unlink()

    def action_requisition(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.requisition",
                "name": "Purchase Requisition",
                "domain": [('it_id','=',int(line.id))],
                'view_mode': 'tree,form',
                'context': {'create': False
                }
            }
