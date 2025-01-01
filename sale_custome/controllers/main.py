import requests
from urllib.parse import parse_qs

import odoo
from odoo import http
import json
from odoo.http import request, _logger
from requests.auth import HTTPBasicAuth
import logging
import pytz
import datetime
import threading


class SaleOrderController(http.Controller):
    @http.route('/sale/get_inquiry', type='json', auth='public', website=True)
    def call_method(self, **kwargs):
        # Call the method of the Odoo model
        result = request.env['request.price'].search([('state', '=', 'draft')])
        a = []
        uid = request.env.uid
        users = request.env['res.users'].browse(uid)
        if users.is_purchase:
            if result:
                for line in result:
                    a.append({
                        'id': int(line.id),
                        'name': str(line.inquiry_id.name)
                    })

        #
        # # Format the result as JSON
        # result_json = json.dumps(result)

        return a

    @http.route('/api/testCOnnection', type='json', auth="none")
    def TestCOnnection(self):
        db = 'rexline'
        uid = request.session.authenticate('rexline', 'admin', 'admin123')
        request.session.db = 'rexline'
        request.session.uid = odoo.SUPERUSER_ID
        users = request.env['res.users'].search([])
        return {
            "message": "Connesction",
            "data": users,
            "database": request.db
        }

    @http.route('/web/attendance', type='json', auth="none")
    def apiAttandance(self):
        db = 'rexline'
        uid = request.session.authenticate('rexline', 'admin', 'admin123')
        request.session.db = 'rexline'
        request.session.uid = odoo.SUPERUSER_ID
        data = request.params
        employee = request.env['hr.employee'].search(
            [('id', '=', data['ref_id'])])
        if not employee:
            return {
                "message": "employee not found"
            }
            exit()
        day = int(str(data['attendance_date'].split('-')[2]))
        month = int(str(data['attendance_date'].split('-')[1]))
        year = int(str(data['attendance_date'].split('-')[0]))
        # return data
        date = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        registry = odoo.modules.registry.Registry(request.session.db)
        with registry.cursor() as cr:
            local = pytz.timezone("Asia/Jakarta")
            clock_in = False
            clock_innn = "00:00:00"
            if data['clock_in']:
                clock_innn = data['clock_in']
            if str(clock_innn) != '00:00:00':
                naive_ci = datetime.datetime.strptime(str(str(date) + " " + str(clock_innn)), "%Y-%m-%d %H:%M:%S")
                local_dt_ci = local.localize(naive_ci, is_dst=None)
                clock_in = str(local_dt_ci.astimezone(pytz.utc)).split("+")[0]

            clock_out = False
            clock_outtt = "00:00:00"
            if data['clock_out']:
                clock_outtt = data['clock_out']
            if str(clock_outtt) != '00:00:00':
                naive_co = datetime.datetime.strptime(str(str(date) + " " + str(clock_outtt)), "%Y-%m-%d %H:%M:%S")
                local_dt_co = local.localize(naive_co, is_dst=None)
                clock_out = str(local_dt_co.astimezone(pytz.utc)).split("+")[0]

            cr.execute("SELECT * FROM hr_attendance WHERE check_in::date = '" + str(
                date) + "' and check_out is null  and employee_id = " + str(employee.id))
            hr_attendance = cr.dictfetchall()

            if hr_attendance != []:
                for line in hr_attendance:
                    request.env['hr.attendance'].search([('id', '=', int(line['id']))]).write({'check_out': clock_out})
            else:
                request.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': clock_in,
                    'check_out': clock_out
                })

    @http.route('/test/postime', type='json', auth='none')
    def test_get(self):
        rec = request.params
        # request.session.authenticate(db, login, password)
        db = 'rexline'
        uid = request.session.authenticate('rexline', 'admin', 'admin123')
        request.session.db = 'rexline'
        request.session.uid = odoo.SUPERUSER_ID
        employe_id = request.env['hr.employee'].search([('id', '=', rec['ref_id'])])

        cek = request.env['hr.leave'].search(
            [('employee_id', '=', int(employe_id.id)), ('date_from', '=', rec['date_from'])])

        # args = {'failed': True, 'message': 'User not found', "ID": cek.id}
        # try:
        if cek:
            args = {'failed': True, 'message': 'you already take this time', "Code": 400}
        else:
            data_req = request.env['hr.leave'].create({
                'name': rec['name'],
                'employee_id': employe_id.id,
                'department_id': employe_id.department_id.id,
                'date_from': rec['date_from'],
                'date_to': rec['date_to'],
                'number_of_days': 1,
                'holiday_status_id': 1
            })
            args = {'success': True, 'message': 'Success', "ID": data_req.id}

        # except:
        # args = {'failed': True, 'message': 'Error', "Code": 400}
        return args
