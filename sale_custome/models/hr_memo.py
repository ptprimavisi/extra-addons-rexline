from odoo import api, models, fields
import requests
from odoo.exceptions import UserError
import json


class HrMemo(models.Model):
    _name = 'hr.memo'
    _description = 'Hr Memo'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    subject = fields.Char()
    content = fields.Html()
    date = fields.Date(default=lambda self: fields.Datetime.today())
    employee_ids = fields.Many2many('hr.employee')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'hr.memo')],
        string='Attachments'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ])

    def action_mark_done(self):
        for line in self:
            line.state = 'done'

    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('MEMO') or '/'
        return super(HrMemo, self).create(vals)

    def action_send_send(self):
        # """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        # self.ensure_one()
        # # self.order_line._validate_analytic_distribution()
        # lang = self.env.context.get('lang')
        # # mail_template = self._find_mail_template()
        # # if mail_template and mail_template.lang:
        # #     lang = mail_template._render_lang(self.ids)[self.id]
        # ctx = {
        #     'default_model': 'hr.memo',
        #     'default_res_ids': self.ids,
        #     # 'default_template_id': mail_template.id if mail_template else None,
        #     'default_composition_mode': 'comment',
        #     'mark_so_as_sent': True,
        #     'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        #     'proforma': self.env.context.get('proforma', False),
        #     'force_email': True,
        #     'model_description': self.subject,
        #     'default_subject': self.subject,
        # }
        # return {
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'mail.compose.message',
        #     'views': [(False, 'form')],
        #     'view_id': False,
        #     'target': 'new',
        #     'context': ctx,
        # }
        for line in self:
            attachment = [(4, att.id) for att in line.attachment_ids]
            email = []
            for lines in line.employee_ids:
                if lines.work_email:
                    email.append(lines.work_email)
                else:
                    if lines.private_email:
                        email.append(lines.private_email)
                    else:
                        raise UserError('Missing Work Email / Private Email!')
                        exit()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email Send',
            'view_mode': 'form',
            'res_model': 'hr.mail.memo',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_employee_ids': self.employee_ids.ids,
                'default_subject': self.subject,
                'default_content': self.content,
                'attachment': attachment,
                'res_id': int(line.id)
            }
        }
