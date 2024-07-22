from odoo import models, api, fields
from odoo.exceptions import UserError


class SyncSo(models.TransientModel):
    _name = 'sinkron.wizard.so'

    start_date = fields.Date()
    end_date = fields.Date()

    def action_save(self):
        raise UserError('Finished')
