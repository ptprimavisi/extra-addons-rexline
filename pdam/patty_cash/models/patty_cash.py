from odoo import api, fields, models


class PermintaanDana(models.Model):
    _name = 'permintaan.dana'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    date = fields.Date()
    user_id = fields.Many2one('res.users')
    dana_line = fields.One2many('permintaan.dana.line', 'permintaan_id')

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('DANA') or '/'
        return super(PermintaanDana, self).create(vals)


class PermintaanLine(models.Model):
    _name = 'permintaan.dana.line'

    description = fields.Char()
    amount = fields.Float()
    permintaan_id = fields.Many2one('permintaan.dana')
