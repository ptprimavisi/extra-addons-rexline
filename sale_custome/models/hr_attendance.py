from odoo import api, models, fields
import requests
from odoo.exceptions import UserError
import json


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def write(self, vals):
        url = f'https://rexline.primasen.id/api/update_users'
        headers = {
            'Content-Type': 'application/json',
        }
        if 'work_email' in vals and vals['work_email']:
            data = {
                "id": vals['id'],
                "email": vals['work_email']
            }
            requests.post(url, headers=headers, data=json.dumps(data))
        else:
            if 'private_email' in vals and vals['private_email']:
                data = {
                    "id": vals['id'],
                    "email": vals['private_email']
                }
                requests.post(url, headers=headers, data=json.dumps(data))
        return super(HrEmployee, self).write(vals)

    def action_sync_employee(self):
        url = f'https://rexline.primasen.id/api/attendance/cek-users'

        # Melakukan permintaan GET ke API eksternal
        response = requests.get(url)
        # print(response)
        # raise UserError('TET')

        # Mengecek apakah permintaan berhasil
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                # Mengambil data user dari response API
                lst_id = []
                user_data = data['data']
                for users in user_data:
                    lst_id.append(users['ref_id'])
                employee = self.env['hr.employee'].search([('id', 'not in', lst_id)])
                print(employee)
                if employee:
                    for employes in employee:
                        urls = 'https://rexline.primasen.id/api/attendance/add-users'

                        if employes.work_email:
                            email = employes.work_email
                        if employes.private_email:
                            email = employes.private_email
                        data = {
                            "name": str(employes.name),
                            "email": email or '',
                            "role": 3,
                            "password": 'rexline123',
                            "id": int(employes.id)
                        }
                        headers = {
                            'Content-Type': 'application/json',
                            # 'Authorization': 'Bearer your_access_token',  # Jika ada token atau autentikasi lainnya
                        }

                        # Melakukan permintaan POST ke API eksternal
                        responses = requests.post(urls, headers=headers, data=json.dumps(data))
                        print(responses)
            else:
                print('User Data not found')
                # Jika user tidak ditemukan
                # self.env.user.notify_warning('User not found.')
        else:
            # Jika permintaan gagal
            # self.env.user.notify_warning('Failed to access external API.')

            print('User Data Not Found')
        # for line in self:

    def action_report_manpower(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "report.manpower",
            "context": {"create": True},
            "name": "Report Manpower",
            "target": "new",
            'view_mode': 'form',
        }


class HrContarct(models.Model):
    _inherit = 'hr.contract'

    position_allowance = fields.Monetary()
    backpay_salary = fields.Monetary()
    transport_allowance = fields.Monetary()
    schedule_type_id = fields.Many2one('hari.kerja')


class MasterHari(models.Model):
    _name = 'master.hari'

    name = fields.Char()


class HariKerja(models.Model):
    _name = 'hari.kerja'

    name = fields.Char()
    hari_id = fields.Many2many('master.hari')
