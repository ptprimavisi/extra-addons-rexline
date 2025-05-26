from odoo import fields, models, api
from odoo.exceptions import UserError


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    location_rak = fields.Many2many('location.tag')


class LocationTag(models.Model):
    _name = 'location.tag'
    _description = 'Location Tags'

    name = fields.Char()
