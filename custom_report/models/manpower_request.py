from odoo import models, fields, api, _
from odoo.fields import Date
import pytz
from odoo.exceptions import UserError
from num2words import num2words
import base64
from collections import defaultdict
from datetime import datetime, timedelta,date
import re


class ManpowerRequestInherit(models.Model):
    _inherit = 'manpower.request'

    def format_date(self,date):
        date_form = date
        show = date_form.strftime('%d-%m-%Y')
        return show

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
                    datetime_utc = lines.write_date  # record = instance dari model

                    # Set timezone lokal
                    tz = pytz.timezone('Asia/Jakarta')

                    # Konversi ke lokal timezone
                    datetime_local = datetime_utc.astimezone(tz)

                    # Format jika diperlukan
                    formatted = datetime_local.strftime('%d-%m-%Y %H:%M:%S')
                    approval_list.append({
                        'name': str(lines.name),
                        'status': str(lines.state),
                        'users': str(lines.user_id.name),
                        'date': str(formatted),
                    })
            return approval_list

    def action_print(self):
        for line in self:
            # test = self.approval_data()
            # print(test)
            # exit()
            # manpower_line = self.manpower_line()
            # print(manpower_line)
            # exit()
            return self.env.ref('custom_report.action_manpower_request').with_context(
                paperformat=4, landscape=False).report_action(self)

    def manpower_line(self):
        result = {}
        for line in self.manpower_ids:
            division_name = line.division_id.name
            position_name = line.position_id.name
            required_qty = line.required_qty
            hr_feedback = line.hr_feedback
            replacement = line.replacement
            day_required = line.day_required
            existing_required = line.existing_required
            remark = line.remark
            state = line.state

            if division_name not in result:
                result[division_name] = []

            result[division_name].append({
                "position_name": position_name,
                "required_qty": required_qty,
                "hr_feedback": hr_feedback,
                "replacement": replacement,
                "day_required": day_required,
                "existing_required": existing_required,
                "remark": remark,
                "state": state,
            })
        return result




