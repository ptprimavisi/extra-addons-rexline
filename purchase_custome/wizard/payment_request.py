from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class PaymentRequest(models.TransientModel):
    _name = 'payment.request.wizard'
    _description = 'Payment Request Wizard'

    request_payment_id = fields.Many2one('payment.request.dp')
    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary(currency_field="currency_id")
    partner_id = fields.Many2one('res.partner')
    journal_id = fields.Many2one('account.journal', domain=[('type', 'in', ['bank', 'cash'])])
    date = fields.Date(default=lambda self: datetime.today())

    def action_payment(self):
        for line in self:
            payment = self.env['account.payment'].create({
                'request_payment_id': int(line.request_payment_id.id),
                'amount': line.amount,
                'currency_id': line.currency_id.id,
                'partner_id': line.partner_id.id,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'journal_id': line.journal_id.id,
            })
            # if payment:
            payment.action_post()
            # return True

