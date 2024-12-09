from odoo import fields, api, models
from odoo.exceptions import UserError


class HrSuratTugas(models.Model):
    _name = 'hr.surat.tugas'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Surat Tugas'

    name = fields.Char()
    sale_id = fields.Many2one('sale.order')
    date_from = fields.Date()
    date_to = fields.Date()
    meal_allowance = fields.Monetary()
    site_allowance = fields.Monetary()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    sura_tugas_line = fields.One2many('hr.surat.tugas.line', 'surat_id')

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('ST') or '/'
        return super(HrSuratTugas, self).create(vals)


class HrSuratTugasLine(models.Model):
    _name = 'hr.surat.tugas.line'
    _description = 'Surat Tugas Line'

    surat_id = fields.Many2one('hr.surat.tugas')
    employee_id = fields.Many2one('hr.employee')
    position = fields.Char()
