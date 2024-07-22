from odoo import api,models, fields
from datetime import datetime

class PaymentWizard(models.TransientModel):
    _name = 'payment.wizard'

    bs_id = fields.Many2one('surat.berharga')
    amount = fields.Float()
    partner_id = fields.Many2one('res.partner')
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive')
    ])
    partner_type = fields.Char()
    journal_id = fields.Many2one('account.journal', domain="[('type','in', ['cash','bank'])]")

    def action_confirm(self):
        for line in self:
            payment = self.env['account.payment'].create({
                'bs_id' : line.bs_id.id,
                'payment_type' : line.payment_type,
                'partner_id': line.partner_id.id,
                'date': datetime.now(),
                'amount': line.amount,
                'ref' : line.bs_id.name,
                'journal_id': line.journal_id.id,
                # 'payment_method_line_id': 3,
            })
            payment.action_post()
            bs = self.env['surat.berharga'].browse(line.bs_id.id)
            user = self.env['res.users'].browse(self.env.uid)
            bs.message_post(body=f'{user.name} Telah melakukan pembayaran')
            bs.write({'state': 'payment',
                      'payment_date': datetime.now()
                      })