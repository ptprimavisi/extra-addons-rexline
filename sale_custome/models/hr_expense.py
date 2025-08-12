from odoo import api, models, fields
import requests
from odoo.exceptions import UserError
import json


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    type_expense = fields.Selection([
        ('reimbursement', 'Reimbursement'),
        ('payment', 'Payment Request')
    ], default="reimbursement")
    line_ids = fields.One2many('hr.expense.items', 'expense_id')
    total_amounts = fields.Float(compute="_compute_totals")

    @api.depends('line_ids')
    def _compute_totals(self):
        for line in self:
            line_ids = line.line_ids
            total = sum(line_ids.mapped('amount'))
            line.total_amount = total

    @api.onchange('total_amounts')
    def onchange_totals(self):
        for line in self:
            line.total_amount_currency = line.total_amounts



class HrExpenseLine(models.Model):
    _name = 'hr.expense.items'

    expense_id = fields.Many2one('hr.expense')
    name = fields.Char()
    amount = fields.Float()
    remark = fields.Char()
