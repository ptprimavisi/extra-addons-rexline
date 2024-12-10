from odoo import fields, models, api
from odoo.exceptions import UserError


class MaintenanceReport(models.Model):
    _name = 'maintenance.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Maintenance Report'

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    date = fields.Date()
    type = fields.Selection([
        ('geps', 'GEPS'),
        ('cctv', 'CCTV'),
        ('maintenance', 'Maintenance'),
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'maintenance.report')],
        string='Attachments'
    )

    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('MNT') or '/'
        return super(MaintenanceReport, self).create(vals_list)

