from odoo import fields, models, api
from odoo.exceptions import UserError


class GaAssets(models.Model):
    _name = 'ga.assets'
    _description = 'GA Assets Management'

    name = fields.Char()
    number = fields.Char()
    location = fields.Char()
    jumlah = fields.Float()
    no_plat = fields.Char()
    no_rangka = fields.Char()
    no_mesin = fields.Char()
    remark = fields.Char()
    insurance = fields.Char()
    start = fields.Date()
    expired = fields.Date()
    asset_type = fields.Selection([
        ('furniture', 'Furniture'),
        ('electric', 'Electric'),
        ('vehicle', 'Vehicle'),
        ('rental', 'Rental'),
    ])
