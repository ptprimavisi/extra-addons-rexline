from odoo import fields, models, api
from datetime import date
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
        ('leasing', 'Leasing'),
        ('heavy_equipment', 'Heavy Equipment'),
        ('machinery', 'Machinery')
    ])

    stnk = fields.Char('STNK')
    username = fields.Char('Username')
    purchase_date = fields.Date('Purchase Date')
    tahun_buat = fields.Char('Production Year')
    merk = fields.Char('Merk')
    bbm = fields.Char('Fuel Type')
    capacity_pass = fields.Integer()

    days_remaining = fields.Integer(compute='compute_days_remainings', store=True)
    sisa_hari = fields.Char(string='Days Remaining', compute="compute_days_remainings")

    @api.depends('expired')
    def compute_days_remainings(self):
        today = date.today()
        for record in self:
            if record.expired:
                delta = (record.expired - today).days
                record.days_remaining = delta
                record.sisa_hari = f"In {delta} Days" if delta >= 0 else f"Expired"
            else:
                record.days_remaining = 0
                record.sisa_hari = "-"
