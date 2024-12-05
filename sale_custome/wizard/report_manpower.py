from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import io
import xlsxwriter
import base64


class ReportManpower(models.TransientModel):
    _name = 'report.manpower'

    sale_id = fields.Many2one('sale.order')

    def action_generate(self):
        for line in self:
            # for line in self:
            so = line.sale_id
            # line.mrp_production_count = 0
            ids = []
            if so:
                mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
                for mos in mo:
                    ids.append(mos.id)
                    sub_mo_ids = mos._get_children().ids
                    order1 = self.env['mrp.production'].search([('id', 'in', sub_mo_ids)])
                    if order1:
                        for moss in order1:
                            ids.append(moss.id)
                            order2 = self.env['mrp.production'].search([('id', 'in', moss._get_children().ids)])
                            if order2:
                                for mosss in order2:
                                    ids.append(mosss.id)
                                    order3 = self.env['mrp.production'].search(
                                        [('id', 'in', mosss._get_children().ids)])
                                    if order3:
                                        for mossss in order3:
                                            ids.append(mossss.id)
                                            order4 = self.env['mrp.production'].search(
                                                [('id', 'in', mossss._get_children().ids)])
                                            if order4:
                                                for mosssss in order4:
                                                    ids.append(mosssss.id)
            prod_report = self.env['production.report'].search([('mo_id','in',ids),('state','=','done')])
            manpower_ids = []
            list_manpower = []
            if prod_report:
                manpower = self.env['man.power.line'].search([('report_id.schedule_id','in', prod_report.ids)])
                for mans in manpower:
                    list_manpower.append({
                        'employee': mans.employee_id.name,
                        'position': mans.position,
                        'work_hour': mans.work_hours
                    })
            print(list_manpower)
