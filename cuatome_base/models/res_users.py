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
