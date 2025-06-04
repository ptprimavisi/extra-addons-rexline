from abc import ABC

from odoo import models, api, fields
from odoo.exceptions import UserError


class InquirySales(models.Model):
    _inherit = 'res.users'

    is_purchase = fields.Boolean()
    is_ga = fields.Boolean()
    is_engineering = fields.Boolean()
    is_accounting = fields.Boolean()
    is_inventory = fields.Boolean()
    is_planner = fields.Boolean()
    is_sales = fields.Boolean()
    is_production = fields.Boolean()
    is_hr = fields.Boolean()
    is_operation = fields.Boolean()


class MultiApproval(models.Model):
    _inherit = 'multi.approval'

    user_domain = fields.Char(compute="_user_domain", search="_search_domain")

    def _user_domain(self):
        uid = self.env.uid
        self.user_domain = self.env['res.users'].search([('id', '=', uid)])

    def _search_domain(self, operator, value):
        uid = self.env.uid
        if uid in [1, 2]:
            domain = [("id", '!=', False)]
        else:
            domain = ['|', ('user_id', '=', int(uid)), ('pic_id', '=', int(uid))]
        return domain
