##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from odoo import models
from odoo.exceptions import UserError


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        self.env["multi.approval.type"].check_rule(self, vals)
        res = super().write(vals)
        return res

    def unlink(self):
        res = super().unlink()
        active_model = self.env.context.get('params', {}).get('model')
        active_id = self.env.context.get('params', {}).get('id')
        print(self.env.context)
        # res = super().unlink()
        if active_model and active_id:
            model = f"{active_model}"
            id = active_id
            record = self.env[model].search([('id', '=', id)])
            if record:
                origin_ref = f"{active_model},{id}"
                approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
                if approval:
                    uniq = int(record.id)
                    if 'name' in record._fields:
                        uniq = record.name
                    message = f'The record ({uniq}) has been deleted'
                    approval.message_post(body=message)
        return res
