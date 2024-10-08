from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ReportAr(models.TransientModel):
    _name = 'report.ar'

    date_from = fields.Date()
    date_to = fields.Date()

    def action_generate(self):
        for line in self:
            if line.date_from > line.date_to:
                list = []
                raise UserError('Tanggal Mulai Harus lebih Kecil')
            list = []
            invoice_before_partial = self.env['account.move'].search([('state','=', 'posted'), ('move_type','=','out_invoice'), ('payment_state','=','partial'), ('invoice_date','<', line.date_from), ('amount_residual','!=',0)])
            invoice_before_notpaid = self.env['account.move'].search([('state','=', 'posted'), ('move_type','=','out_invoice'), ('payment_state','=','not_paid'), ('invoice_date','<', line.date_from), ('amount_residual','=',0)])

            partial_before = sum(invoice_before_partial.mapped('amount_residual'))
            notpaid_before = sum(invoice_before_notpaid.mapped('amount_total'))

            partial_after = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('payment_state', '=', 'partial'), ('invoice_date', '>=', line.date_from),
                 ('invoice_date', '<=', line.date_to), ('residual_amount','!=', 0)])
            notpaid_after = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('payment_state', '=', 'not_paid'), ('invoice_date', '>=', line.date_from),
                 ('invoice_date', '<=', line.date_to), ('residual_amount', '=', 0)])
            partial_baru = sum(partial_after.mapped('amount_residual'))
            not_paid_baru = sum(notpaid_after.mapped('amount_total'))
            list.append({
                'saldo_awal': partial_before + notpaid_before,
                'piutang_baru': partial_baru + not_paid_baru
            })