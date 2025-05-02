from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    def action_print(self):
        for line in self:
            return self.env.ref('custom_report.action_report_crm').with_context(
                paperformat=4, landscape=True).report_action(self)
