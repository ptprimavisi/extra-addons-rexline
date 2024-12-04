from odoo import api, fields, models
from odoo.exceptions import UserError

class InheritRequestPrice(models.Model):
    _inherit='request.price'

    due_date = fields.Datetime(string="Due Date")


class InheritRequestPrice(models.Model):
    _inherit='request.price.wizard'

    due_date = fields.Datetime(string="Due Date", compute="_compute_due_date", store=True)

    @api.depends('inquiry_id')
    def _compute_due_date(self):
        for record in self:
            if record.inquiry_id:
                record.due_date = record.inquiry_id.due_date
            else:
                record.due_date = False