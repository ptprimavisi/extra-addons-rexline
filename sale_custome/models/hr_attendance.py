from odoo import api, models, fields
import requests
from odoo.exceptions import UserError
import json


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def write(self, vals):
        for line in self:
            url = f'https://rexline.primasen.id/api/update_users'
            headers = {
                'Content-Type': 'application/json',
            }
            if line.work_email:
                data = {
                    "id": int(line.id),
                    "email": line.work_email
                }
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)

                    if response.status_code == 200:
                        print("Berhasil:", response.json())
                    else:
                        print(f"Gagal. Status code: {response.status_code}, Response: {response.text}")

                except requests.exceptions.ConnectTimeout:
                    print("Koneksi ke server timeout. Cek koneksi internet atau apakah server aktif.")

                except requests.exceptions.ConnectionError:
                    print("Tidak bisa terhubung ke server. Cek URL atau koneksi jaringan.")

                except requests.exceptions.RequestException as e:
                    print("Terjadi error lain saat mengirim request:", e)
            else:
                if line.private_email:
                    data = {
                        "id": int(line.id),
                        "email": line.private_email
                    }
                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)

                        if response.status_code == 200:
                            print("Berhasil:", response.json())
                        else:
                            print(f"Gagal. Status code: {response.status_code}, Response: {response.text}")

                    except requests.exceptions.ConnectTimeout:
                        print("Koneksi ke server timeout. Cek koneksi internet atau apakah server aktif.")

                    except requests.exceptions.ConnectionError:
                        print("Tidak bisa terhubung ke server. Cek URL atau koneksi jaringan.")

                    except requests.exceptions.RequestException as e:
                        print("Terjadi error lain saat mengirim request:", e)
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
                        if not employes.work_email and employes.private_email:
                            str_err = f"Plesae fill private email and work email first ({employes.name})"

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


class HrleaveInhrith(models.Model):
    _inherit = 'hr.leave'

    def update_status(self, status):
        for line in self:
            url = f'https://rexline.primasen.id/api/timeOff/update_status'
            headers = {
                'Content-Type': 'application/json',
                # 'Authorization': 'Bearer your_access_token',  # Jika ada token atau autentikasi lainnya
            }
            body = {
                "user_id": line.employee_id.id,
                "date": str(line.request_date_from),
                "status": status
            }
            requests.post(url, headers=headers, data=json.dumps(body))

    def action_approve(self):
        res = super(HrleaveInhrith, self).action_approve()
        self.update_status(1)
        return res

    def action_refuse(self):
        res = super(HrleaveInhrith, self).action_refuse()
        self.update_status(2)
        return res

    def action_draft(self):
        res = super(HrleaveInhrith, self).action_refuse()
        self.update_status(0)
        return res
