from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
from datetime import date


class GaMaintenanceWizard(models.TransientModel):
    _name = 'ga.maintenance.wizard'

    notification_date = fields.Date()
    user_ids = fields.Many2many('res.users')
    summary = fields.Text()
    note = fields.Html()

    def action_send_schedule(self):
        for line in self:
            res_id = self.env.context.get('res_id', False)
            if line.user_ids and line.notification_date:
                user = self.env['res.users'].search([('id','in', line.user_ids.ids)])
                maintenance = self.env['ga.maintenance.report'].search([('id','=',int(res_id))])
                for lines in user:
                    if maintenance:
                        maintenance.activity_schedule(
                            activity_type_id= 4,
                            automated=False,
                            summary=line.summary,
                            note=line.note,
                            user_id=int(lines.id),
                            date_deadline=line.notification_date
                        )
                    else:
                        raise UserError('Maintenance ID not found')

