from odoo import fields, models, api


class InquiryInherit(models.Model):
    _inherit = 'inquiry.inquiry'

    def action_print(self):
        return self.env.ref('custom_report.action_report_inquiry').with_context(
            paperformat=4, landscape=True).report_action(self)
