from odoo import fields, models, api
from odoo.exceptions import UserError


class GaMaintenanceReport(models.Model):
    _name = 'ga.maintenance.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'GA Maintenance Report '

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    date = fields.Date()
    type = fields.Selection([
        ('gps', 'GPS'),
        ('cctv', 'CCTV'),
        ('maintenance', 'Maintenance'),
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'ga.maintenance.report')],
        string='Attachments'
    )

    def action_done(self):
        for line in self:
            line.state = 'done'

    def action_draft(self):
        for line in self:
            line.state = 'draft'

    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('GAMNT') or '/'
        return super(GaMaintenanceReport, self).create(vals_list)

    def action_create_schedule(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "ga.maintenance.wizard",
            "name": "Schedule",
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'res_id': int(self.id),
            }
        }


