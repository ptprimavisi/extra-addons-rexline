from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bs_id = fields.Many2one('surat.berharga')


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    total_amount = fields.Float(compute="compute_amount_total")

    @api.depends('line_ids.price_unit', 'line_ids.product_qty')
    def compute_amount_total(self):
        for line in self:
            cost = 0
            for lines in line.line_ids:
                total = lines.price_unit * lines.product_qty
                cost += total
            line.total_amount = cost


class PermintaanDana(models.Model):
    _name = 'surat.berharga'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    document_type = fields.Char()
    reference = fields.Char()
    date = fields.Date(default=lambda self: datetime.now())
    partner_id = fields.Many2one('res.partner')
    requisition_id = fields.Many2one(
        'purchase.requisition',
        domain="[('state', 'not in', ['draft', 'cancel', 'done'])]"
    )
    description = fields.Char()
    note = fields.Text()
    due_date = fields.Date()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    payment_date = fields.Date()
    amount = fields.Float()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approve'),
        ('payment', 'Payment'),
    ], default='draft')
    count_payment = fields.Float(compute="_compute_payment")

    def action_count_payment(self):
        for line in self:
            result = {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "domain": [('bs_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "Vendor Payment",
                'view_mode': 'tree,form',
            }
            return result

    def _compute_payment(self):
        for line in self:
            price = 0
            payment = self.env['account.payment'].search([('bs_id','=',int(line.id)), ('state','=', 'posted')])
            if payment:
                for pays in payment:
                    price += pays.amount
            line.count_payment = price


    @api.onchange('requisition_id')
    def action_requisition(self):
        for line in self:
            line.amount = False
            line.partner_id = False
            if line.requisition_id:
                line.amount = line.requisition_id.total_amount
                line.partner_id = line.requisition_id.vendor_id

    def unlink(self):
        for line in self:
            if line.state == 'approve':
                raise UserError('Tidak daoat menghapus dokumen yang sudah di approve')
            elif line.state == 'payment':
                raise UserError('Tidak dapat menghapus dokumen yg sudah di lunasi')
            return True

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('BS') or '/'
        return super(PermintaanDana, self).create(vals)

    def action_confirm(self):
        for line in self:
            line.state = 'approve'
            user = self.env['res.users'].browse(self.env.uid)
            line.message_post(body=f'{user.name} Approve this document')

    def action_payment(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "payment.wizard",
                "name": "Create Payment",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    "create": False,
                    'default_bs_id': int(line.id),
                    'default_amount': line.amount,
                    'default_partner_id': line.partner_id.id,
                    'default_payment_type': 'outbound',
                    'default_partner_type': 'supplier',
                    'search_default_outbound_filter': 1,
                    'default_move_journal_types': ('bank', 'cash'),
                    'display_account_trust': True,
                }
            }

