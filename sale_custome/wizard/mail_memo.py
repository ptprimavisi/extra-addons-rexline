import base64
import io
from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging


class MailMemo(models.TransientModel):
    _name = 'hr.mail.memo'
    _description = 'Hr Mail Memo'

    employee_ids = fields.Many2many('hr.employee')
    subject = fields.Char()
    content = fields.Html()

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'hr.mail.memo')],
        string='Attachments'
    )

    def email_send(self, res_id, subject, content, email_from, email_to):
        attachments = self.env.context.get('attachment', False)
        message = self.env["mail.message"].create(
            {
                "subject": subject,
                "model": self._name,
                "res_id": res_id,
                "body": content,
            }
        )
        res_id = self.env.context.get('res_id', False)
        memo = self.env['hr.memo'].search([('id','=',res_id)])
        memo.message_post(
            body=content,
            subject=subject,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",  # Bisa ganti ke subtype lain jika perlu
        )

        mail = self.env["mail.mail"].sudo().create(
            {
                "mail_message_id": message.id,
                "body_html": content,
                "email_to": email_to,
                "email_from": email_from,
                "attachment_ids": attachments,
                "auto_delete": True,
                "state": "outgoing",
            }
        )
        # mail.send()

    def send_request_mail(self):
        for line in self:
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
            for emails in email:
                self.email_send(int(line.id), line.subject, line.content, line.create_uid.email, emails)

