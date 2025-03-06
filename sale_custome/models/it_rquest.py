from odoo import fields, models, api
from odoo.exceptions import UserError


class ItRequest(models.Model):
    _name = 'it.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid, domain=lambda self: [('id', '=', self.env.uid)])
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1))
    department_id = fields.Many2one('hr.department', compute="_compute_department", store=True)
    date_request = fields.Date(default=lambda self: fields.Datetime.today())
    due_date = fields.Date()
    description = fields.Text()
    justification = fields.Text()
    estimate_price = fields.Float()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    count_requisition = fields.Integer(compute="_count_requisition")
    requisition_state = fields.Selection([
        ('to_requisition', 'To Requisition'),
        ('requisition', 'Requisition')
    ], compute="_compute_requisition_state")
    user_domain = fields.Char(compute="_user_domain", search="_search_domain")
    active = fields.Boolean(default=True)

    @api.depends('count_requisition')
    def _compute_requisition_state(self):
        for line in self:
            line.requisition_state = 'to_requisition'
            if line.count_requisition > 0:
                line.requisition_state = 'requisition'

    def _user_domain(self):
        uid = self.env.uid
        self.user_domain = self.env['res.users'].search([('id','=',uid)])

    def _search_domain(self, operator, value):
        uid = self.env.uid
        print(uid)
        if self.env.user.has_group('sale_custome.it_custom_group') and uid not in [1,2]:
            domain = ["|", ('state', '=', 'done'), ("user_id", '=', int(uid))]
        else:
            if uid == 1 or uid == 2:
                domain = [('id', '!=', False)]
            else:
                domain = [("user_id", '=', int(uid))]
        return domain



    @api.depends('employee_id')
    def _compute_department(self):
        for line in self:
            line.department_id = False
            if line.employee_id and line.employee_id.department_id:
                line.department_id = line.employee_id.department_id.id

    # @api.onchange('employee_id')
    # def oc_employee(self):
    #     for line in self:
    #         line.department_id = False
    #         if line.employee_id:
    #             if line.employee_id.department_id:
    #                 # raise UserError(line.employee_id.department_id)
    #                 line.department_id = line.employee_id.department_id.id

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
            if line.count_requisition > 0:
                raise UserError('This document cannot be deleted, because you have purchase requisition document')
                exit()
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
