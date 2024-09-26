from odoo import models, api, fields
from odoo.exceptions import UserError

class PPHKategori(models.Model):
    _name = 'pph.kategori'

    name = fields.Char(compute="compute_name")
    keterangan = fields.Char()
    kategori = fields.Selection([
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
        ('e', 'E'),
        ('f', 'F'),
        ('g', 'G'),
        ('h', 'H'),
    ])
    tarif_pajak = fields.Float(string="Tarif Pajak (%)")

    def compute_name(self):
        for line in self:
            selection_dict = dict(self._fields['kategori'].selection)

            # Print the label corresponding to the stored value in self.selection
            # print(selection_dict.get(self.selection))
            line.name = str("KATEGORI ") + str(selection_dict.get(line.kategori)) + " - " + str(line.keterangan)


class PTKP_terbaru(models.Model):
    _name = 'ptkp.ptkp.ptkp'

    name = fields.Char()
    nominal = fields.Float()

class hrcontract(models.Model):
    _inherit = 'hr.contract'

    pph_kategori = fields.Many2one('pph.kategori')
    ptkp_id = fields.Many2one('ptkp.ptkp.ptkp')
