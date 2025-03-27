from odoo import models, fields, api, _
from odoo.fields import Date
from odoo.exceptions import UserError
from num2words import num2words
import base64
from collections import defaultdict
from datetime import datetime, timedelta, date
import re


class PurchaseOrderInh(models.Model):
    _inherit = 'purchase.order'

    def action_print(self):
        dates = {}
        return self.env.ref('custom_report.action_report_po').with_context(
            paperformat=4, landscape=False).report_action(self, data=dates)
