from odoo import models, fields, api, _
from odoo.fields import Date
from odoo.exceptions import UserError
from num2words import num2words
import base64
from collections import defaultdict
from datetime import datetime, timedelta,date
import re


class TravelRequestInherith(models.Model):
    _inherit = 'travel.request'

    def action_print(self):
        for line in self:
            return self.env.ref('custom_report.action_travel_request').with_context(
                paperformat=4, landscape=False).report_action(self)
