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

    def approval_data(self):
        for line in self:
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            approval = self.env['multi.approval'].search(
                [('origin_ref', '=', origin_ref)],
                order='create_date desc',
                limit=1
            )
            approval_list = []
            if approval:
                for lines in approval.line_ids:
                    date_confirm = str(lines.write_date)
                    dt = datetime.strptime(date_confirm, "%Y-%m-%d %H:%M:%S.%f")

                    # Format ulang tanpa milidetik
                    result = dt.strftime("%Y-%m-%d %H:%M:%S")
                    approval_list.append({
                        'name': str(lines.name),
                        'status': str(lines.state),
                        'users': str(lines.user_id.name),
                        'date': str(result),
                    })
            return approval_list

    def action_print(self):
        for line in self:
            # test = self.approval_data()
            # print(test)
            # exit()
            return self.env.ref('custom_report.action_travel_request').with_context(
                paperformat=4, landscape=False).report_action(self)
