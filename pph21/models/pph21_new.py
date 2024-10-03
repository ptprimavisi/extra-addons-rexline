from odoo import models, api, fields
from odoo.exceptions import UserError


class PTKP_terbaru(models.Model):
    _name = 'ptkp.ptkp.ptkp'

    name = fields.Char()
    nominal = fields.Float(compute="compute_nominal")
    kategori_pph = fields.Selection([
        ('a', 'TER A'),
        ('b', 'TER B'),
        ('c', 'TER C')
    ], compute='_compute_golongan')

    @api.depends('name')
    def _compute_golongan(self):
        for line in self:
            line.kategori_pph = 'a'
            if line.name:
                if line.name == 'TK/0' or line.name == 'TK/1' or line.name == 'K/0':
                    line.kategori_pph = 'a'
                elif line.name == 'TK/2' or line.name == 'K/1' or line.name == 'TK/3' or line.name == 'K/2':
                    line.kategori_pph = 'b'
                elif line.name == 'K/3':
                    line.kategori_pph = 'c'

    @api.depends('name')
    def compute_nominal(self):
        for line in self:
            line.nominal = 0
            if line.name:
                if line.name == 'TK/0':
                    line.nominal = 54000000
                elif line.name == 'TK/1' or line.name == 'K/0':
                    line.nominal = 58500000
                elif line.name == 'TK/2' or line.name == 'K/1':
                    line.nominal = 63000000
                elif line.name == 'TK/3' or line.name == 'K/2':
                    line.nominal = 67500000
                elif line.name == 'K/3':
                    line.nominal = 70000000


class hrcontract(models.Model):
    _inherit = 'hr.contract'

    ptkp_id = fields.Many2one('ptkp.ptkp.ptkp')
