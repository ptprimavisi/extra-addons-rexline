from odoo import models, api, fields
from datetime import datetime
from odoo.exceptions import UserError


class TableUSers(models.Model):
    _name = 'tbl.users'

    namalengkap = fields.Char()
    username = fields.Char()
    password = fields.Char()
    status = fields.Char()


class FormulirPendaftaran(models.Model):
    _name = 'formulir.pendaftaran'

    user_id = fields.Many2one('res.users')
    posisi = fields.Char()
    name = fields.Char()
    no_ktp = fields.Char()
    ttl = fields.Char()
    jk = fields.Selection([
        ('l', 'LAKI-LAKI'),
        ('p', 'PEREMPUAN')
    ], required=True)
    agama = fields.Char()
    gol_darah = fields.Char()
    status = fields.Char()
    alamat_ktp = fields.Text()
    alamat_tinggal = fields.Text()
    email = fields.Char()
    no_hp = fields.Char()
    no_keluarga = fields.Char()
    pendidikan_ids = fields.One2many('riwayat.pendidikan', 'formulir_id')
    pelatihan_ids = fields.One2many('riwayat.pelatihan', 'formu_id')
    pekerjaan_ids = fields.One2many('riwayat.pekerjaan', 'form_id')
    skill = fields.Text()
    brsedia_ditempatkan = fields.Selection([
        ('ya', 'Ya'),
        ('tidak', 'Tidak')
    ])
    salary = fields.Float()
    file_data = fields.Binary(string="File")
    file_name = fields.Char(string="Filename")
    akses = fields.Boolean(compute="_compute_akses", search="branch_search")

    def _compute_akses(self):
        for line in self:
            uid = self.env.uid
            user = self.env['res.users'].browse(uid)
            line.akses = False
            if user:
                if user.id == 2 or user.id == 1:
                    line.akses = True
                else:
                    if line.user_id == int(user.id):
                        line.akses = True

    def branch_search(self, operator, value):
        # for i in self:
        if self.env.uid == 1 or self.env.uid == 2:
            data = self.env['formulir.pendaftaran'].search([])
            # contract = self.env['hr.contract'].search([('akses', '!=', True)])
            # employee = self.env['hr.employee'].search([('id', 'in', contract.employee_id.ids)])
            # print('lihat employee', contract.id)
            domain = [('id', 'in', data.ids)]
            return domain
        else:
            data = self.env['formulir.pendaftaran'].search([('user_id','=', self.env.uid)])
            domain = [('id', 'in', data.ids)]
            return domain


class RwytPendidikan(models.Model):
    _name = 'riwayat.pendidikan'

    jenjang = fields.Char()
    institude = fields.Char()
    jurusan = fields.Char()
    tahun = fields.Integer()
    ipk = fields.Float()
    formulir_id = fields.Many2one('formulir.pendaftaran')


class RwytPelatihan(models.Model):
    _name = 'riwayat.pelatihan'

    name = fields.Char()
    sertifikat = fields.Char()
    tahun = fields.Integer()
    formu_id = fields.Many2one('formulir.pendaftaran')


class RwytPekerjaan(models.Model):
    _name = 'riwayat.pekerjaan'

    nama = fields.Char()
    posisi = fields.Char()
    pendapatan = fields.Float()
    tahun = fields.Integer()
    form_id = fields.Many2one('formulir.pendaftaran')
