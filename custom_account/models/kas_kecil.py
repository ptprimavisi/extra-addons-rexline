from abc import ABC

from odoo import models, api, fields
from datetime import datetime
from odoo.exceptions import UserError


class JobTittleGM(models.Model):
    _name = 'general.manager'

    general_manager = fields.Many2one('hr.employee', string='General Manager')

    @api.model
    def default_get(self, fields_list):
        res = super(JobTittleGM, self).default_get(fields_list)
        gm = self.search([], limit=1)
        if gm:
            res.update({
                'general_manager': gm.general_manager.id
            })
        return res

    def update(self):
        for rec in self:
            # Buat signature baru
            new_gm = self.env['general.manager'].create({
                'general_manager': rec.general_manager.id

            })
            # Cari semua signature lain
            existing_gm = self.env['general.manager'].search([('id', '!=', new_gm.id)])
            # Hapus semua signature kecuali signature yang baru saja dibuat
            if existing_gm:
                for gm in existing_gm:
                    gm.unlink()


class JobTittleCOO(models.Model):
    _name = 'coo.coo'

    coo = fields.Many2one('hr.employee', string='Chief Operating Officer')

    @api.model
    def default_get(self, fields_list):
        res = super(JobTittleCOO, self).default_get(fields_list)
        coo = self.search([], limit=1)
        if coo:
            res.update({
                'coo': coo.coo.id
            })
        return res

    def update(self):
        for rec in self:
            # Buat signature baru
            new_coo = self.env['coo.coo'].create({
                'coo': rec.coo.id

            })
            # Cari semua signature lain
            existing_coo = self.env['coo.coo'].search([('id', '!=', new_coo.id)])
            # Hapus semua signature kecuali signature yang baru saja dibuat
            if existing_coo:
                for coo in existing_coo:
                    coo.unlink()


class PermintaanDana(models.Model):
    _name = 'permintaan.dana'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    project = fields.Char()
    description = fields.Text()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    date_journal = fields.Date()

    def action_print_report(self):
        for line in self:
            # raise UserError(line.tax_list)
            return self.env.ref('custom_account.action_report_advance_request').with_context(
                paperformat=4, landscape=False).report_action(self)

    def _default_employee(self):
        # for line in self:
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return int(employee.id)

    def default_saldo(self):
        for line in self:
            saldo = 0.0
            data_saldo = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
            if data_saldo:
                saldo = float(data_saldo.saldo)
            return saldo

    employee_id = fields.Many2one('hr.employee')
    date_request = fields.Date(default=lambda self: datetime.now())
    saldo = fields.Float()
    journal_id = fields.Many2one('account.account')
    dana_line = fields.One2many('permintaan.dana.line', 'dana_id')
    source_account = fields.Many2one('account.journal', domain="[('type','in', ['bank','cash','general'])]")
    department = fields.Many2one('hr.department', compute='_compute_department', store=True)
    total_amount = fields.Float(compute="_compute_total_cost")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('transfer', 'Transfer Done')
    ], default='draft')
    count_realisasi = fields.Float(compute='_compute_count_realisasi')
    count_refund = fields.Float(compute="_compute_count_refund")
    bank_note = fields.Text()
    realisasi_status = fields.Char(compute="_compute_state_realisasi")
    manager_approve = fields.Boolean(compute="_compute_manager_approve")
    gm_approve = fields.Boolean(compute="_compute_gm_approve")
    coo_approve = fields.Boolean(compute="_compute_coo_approve")

    def _compute_manager_approve(self):
        for line in self:
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            line.manager_approve = False
            if line.department.manager_id.user_id:
                approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
                print(origin_ref)
                if approval:
                    multi_approval_line = self.env['multi.approval.line'].search(
                        [('approval_id', '=', int(approval.id)),
                         ('user_id', '=', line.department.manager_id.user_id.id),
                         ('state', '=', 'Approved')])
                    if multi_approval_line:
                        line.manager_approve = True

    def _compute_gm_approve(self):
        for line in self:
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            line.gm_approve = False
            if line.department.manager_id.user_id:
                approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
                print(origin_ref)
                if approval:
                    gm = self.env['general.manager'].search([], limit=1)
                    multi_approval_line = self.env['multi.approval.line'].search(
                        [('approval_id', '=', int(approval.id)), ('user_id', '=', int(gm.general_manager.user_id.id)),
                         ('state', '=', 'Approved')])
                    if multi_approval_line:
                        line.gm_approve = True

    def _compute_coo_approve(self):
        for line in self:
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            line.coo_approve = False
            if line.department.manager_id.user_id:
                approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
                print(origin_ref)
                if approval:
                    gm = self.env['coo.coo'].search([], limit=1)
                    multi_approval_line = self.env['multi.approval.line'].search(
                        [('approval_id', '=', int(approval.id)), ('user_id', '=', int(gm.coo.user_id.id)),
                         ('state', '=', 'Approved')])
                    if multi_approval_line:
                        line.coo_approve = True

    def _compute_state_realisasi(self):
        for line in self:
            line.realisasi_status = 'To Realisasi'
            realisasi_draft = self.env['realisasi.dana'].search(
                [('permintaan_id', '=', int(line.id)), ('state', '=', 'draft')])
            realisasi_post = self.env['realisasi.dana'].search(
                [('permintaan_id', '=', int(line.id)), ('state', '=', 'posted')])
            if realisasi_draft:
                line.realisasi_status = 'Draft Realisasi'
            if realisasi_post:
                line.realisasi_status = 'Realisasi'

    def _compute_count_refund(self):
        for line in self:
            line.count_refund = 0.0
            refund = self.env['refund.dana'].search([('dana_id', '=', int(line.id))])
            if refund:
                line.count_refund = float(refund.amount)

    def action_count_refund(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Refund',
            'res_model': 'refund.dana',
            "context": {"create": False},
            'view_mode': 'tree,form',
            'domain': [('dana_id', '=', int(self.id))]
        }

    def _compute_count_realisasi(self):
        for line in self:
            line.count_realisasi = 0.0
            realisasi = self.env['realisasi.dana'].search([('permintaan_id', '=', int(line.id))])
            if realisasi:
                line.count_realisasi = float(realisasi.total_amount)

    def action_count_realisasi(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Realisasi Dana',
            'res_model': 'realisasi.dana',
            "context": {"create": False},
            'view_mode': 'tree,form',
            'domain': [('permintaan_id', '=', int(self.id))]
        }

    def unlink(self):
        for line in self:
            if line.state == 'transfer':
                raise UserError('Tidak dapat menghapus dokumen, Status Posted!')
        return super().unlink()

    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            line.saldo = False
            if line.employee_id:
                data_saldo = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
                # raise UserError(data_saldo.saldo)
                if data_saldo:
                    line.saldo = float(data_saldo.saldo)

            # return int(employee.id)

    @api.depends('user_id')
    def _compute_department(self):
        for line in self:
            if line.user_id:
                line.department = False
                employee = self.env['hr.employee'].search([('user_id', '=', line.user_id.id)])
                if employee.department_id:
                    line.department = employee.department_id.id

    @api.depends('dana_line.amount')
    def _compute_total_cost(self):
        for line in self:
            cost = 0
            for lines in line.dana_line:
                cost += lines.amount
            line.total_amount = cost

    # @api.onchange('employee_id')
    # def oc_employee(self):
    #     employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
    #     raise UserError({'domain': {'employee_id': [('department_id', '=', employee.department_id.id)]}})
    #     return {'domain': {'employee_id': [('department_id', '=', employee.department_id.id)]}}
    # for line in self:
    # if line.employee_id:

    # @api.depends('user_id')
    # def _compute_domain_employee(self):
    #     for line in self:
    #         employee = self.env['hr.employee'].search([('user_id', '=', line.user_id.id)])
    #         # print(employee.department_id)
    #         # if employee:
    #             # print({'domain': {'employee_id': [('department_id', '=', employee.department_id.id)]}})
    #         return {'domain': {'employee_id': [('department_id', '=', employee.department_id.id)]}}

    def action_confirm(self):
        for line in self:
            if not line.dana_line:
                raise UserError('Lines cannot be empty!')
            else:
                for lines in line.dana_line:
                    if not lines.description or not lines.amount:
                        raise UserError('description and amount is mandatory field!')
            self.message_post(body="This document has been confirm.")
            line.state = 'confirm'

    def action_transfer(self):
        for line in self:
            if not line.date_journal:
                raise UserError('Tanggal journal tidak boleh kosong!')
                exit()
            if not line.source_account:
                raise UserError('Source account is mandatory fields!')
            if not line.journal_id:
                raise UserError('Destination account is not set!')
            cek_data_saldo = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
            if not cek_data_saldo:
                self.env['saldo.dana'].create({
                    'employee_id': line.employee_id.id,
                })
            amount = 0.0
            for lines in line.dana_line:
                amount += lines.amount

            saldo_data = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
            # move_journal
            partner_id = self.env['res.users'].browse(line.user_id.id).partner_id
            move = self.env['account.move'].create({
                'journal_id': 3,
                'date': line.date_journal,
                # 'branch_id': line.branch_id.id,
                'ref': line.name,
                'dana_id': int(line.id),
                'line_ids': [
                    (0, 0, {
                        'account_id': line.journal_id.id,
                        'date': line.date_journal,
                        # Ganti dengan akun yang sesuai
                        'name': str(line.name) + " " + str(line.description or ''),
                        'partner_id': int(partner_id.id),
                        'debit': line.total_amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': line.source_account.default_account_id.id,
                        'date': line.date_journal,
                        # Ganti dengan akun yang sesuai
                        'name': str(line.name) + " " + str(line.description or ''),
                        'partner_id': int(partner_id.id),
                        'debit': 0.0,
                        'credit': line.total_amount,
                    }),
                ],
            })

            # credit
            # self.env['account.move.line'].create({
            #     'move_id': move.id,
            #     'account_id': line.source_account.default_account_id.id,
            #     'partner_id': int(partner_id.id),
            #     'credit': line.total_amount,
            #     'name': str(line.name) + " " + str(line.description or '')
            # })
            # # debit
            # self.env['account.move.line'].create({
            #     'move_id': move.id,
            #     'account_id': line.journal_id.id,
            #     'debit': line.total_amount,
            #     'partner_id': int(partner_id.id),
            #     'name': str(line.name) + " " + str(line.description or '')
            # })

            move.action_post()
            update_saldo = saldo_data.saldo + line.total_amount
            saldo_data.write({
                'saldo': float(update_saldo)
            })
        self.message_post(body=f"Transfer success. {str(line.total_amount)}")
        line.state = 'transfer'

    def action_reset_to_draft(self):
        for line in self:
            saldo = self.env['saldo.dana'].search([('employee_id', '=', int(line.employee_id.id))])
            realisasi_dana = self.env['realisasi.dana'].search([('permintaan_id', '=', int(line.id))])
            refund_dana = self.env['refund.dana'].search([('dana_id', '=', int(line.id))])
            if realisasi_dana:
                raise UserError('Sudah dilakukan realisasi, batalkan dan hapus realisasi terlebih dahulu!')
                exit()
            if refund_dana:
                raise UserError('Sudah dilakukan refund, batalkan dan hapus refund terlebih dahulu!')
                exit()
            saldo_update = saldo.saldo - line.total_amount
            saldo.write({'saldo': saldo_update})
            journal = self.env['account.move'].search([('dana_id', '=', int(line.id))])
            journal.button_draft()
            journal.unlink()
            line.state = 'confirm'

    def action_realisasi(self):
        for line in self:
            saldo = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)]).saldo
            realisasi = self.env['realisasi.dana'].search([('permintaan_id', '=', line.id), ('state', '=', 'draft')])
            if saldo <= 0.0:
                raise UserError('Saldo anda 0')
                exit()
            if realisasi:
                saldo = float(saldo) - float(realisasi.saldo)
                if saldo <= 0.0:
                    raise UserError('Saldo anda 0')
                    exit()
            self.message_post(body=f"Realisasi Created.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Realisasi Dana',
                'res_model': 'realisasi.dana',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'permintaan_id': int(line.id),
                    'saldo': float(saldo),
                    'employee_id': line.employee_id.id,
                    'source_account': line.journal_id.id
                }
            }

    def action_refund(self):
        for line in self:
            saldo = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)]).saldo
            realisasi = self.env['realisasi.dana'].search([('permintaan_id', '=', line.id), ('state', '=', 'draft')])
            if realisasi:
                saldos = float(saldo) - float(realisasi.total_amount)
                if saldos <= 0.0:
                    raise UserError('Saldo anda 0!')
                    exit()
            if saldo <= 0.0:
                raise UserError('Saldo anda 0!')
                exit()
            # if realisasi:
            #     saldo = float(saldo) - float(realisasi.saldo)
            # if saldo <= 0:
            #     raise UserError(f"Saldo tidak mencukupi, saldo saati ini adalah : {str(saldo)}")
            #     exit()
            # else:
            self.message_post(body=f"Refund Created.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Refund Dana',
                'res_model': 'refund.dana',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'dana_id': int(line.id),
                    'amount': float(saldo),
                    'employee_id': line.employee_id.id,
                    'department_id': line.department.id,
                    'source_account': line.journal_id.id,
                    'dest_account': line.source_account.default_account_id.id
                }
            }

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves['name'] = self.env['ir.sequence'].next_by_code('DANA')
        a = moves['name']
        index = 2
        department = self.env['hr.department'].search([('id', '=', int(moves['department']))])
        if department and department.code:
            code = '-' + str(department.code) or ''
            a = a[:index] + code + a[index:]
        moves['name'] = a
        return moves


class DanaLine(models.Model):
    _name = 'permintaan.dana.line'

    dana_id = fields.Many2one('permintaan.dana')
    description = fields.Text()
    amount = fields.Float()


class RealisasiDana(models.Model):
    _name = 'realisasi.dana'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    project = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    employee_id = fields.Many2one('hr.employee')
    permintaan_id = fields.Many2one('permintaan.dana')
    request_date = fields.Date(default=lambda self: datetime.now())
    source_account = fields.Many2one('account.account')
    saldo = fields.Float()
    realisasi_line = fields.One2many('realisasi.line', 'realisasi_id')
    total_amount = fields.Float(compute="_compute_total_cost", readonly=False)
    department_id = fields.Many2one('hr.department', compute="_compute_department")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')
    ], default='draft')
    advance_amount = fields.Float(compute="_compute_advance_amount")
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'realisasi.dana')],
        string='Attachments'
    )
    date_journal = fields.Date()

    @api.depends('employee_id')
    def _compute_department(self):
        for line in self:
            line.department_id = False
            if line.employee_id.department_id:
                line.department_id = line.employee_id.department_id.id

    @api.depends('permintaan_id')
    def _compute_advance_amount(self):
        for line in self:
            line.advance_amount = line.permintaan_id.total_amount

    def action_print_report(self):
        for line in self:
            # raise UserError(line.tax_list)
            return self.env.ref('custom_account.action_report_ralisasi').with_context(
                paperformat=4, landscape=False).report_action(self)

    def unlink(self):
        for line in self:
            if line.state == 'posted':
                raise UserError('Tidak dapat menghapus dokumen, Status Posted!')
        return super().unlink()

    def action_post(self):
        for line in self:
            if not line.date_journal:
                raise UserError('Tanggal journal tidak boleh kosong!')
                exit()
            if line.total_amount <= 0:
                raise UserError('amount tidak boleh 0.0')
            if not line.realisasi_line:
                raise UserError('lines item tidak boleh kosong')
            if line.total_amount > line.saldo:
                raise UserError('saldo tidak mencukupi')
            for linesss in line.realisasi_line:
                if not linesss.account_id:
                    raise UserError('account id tidak boleh kosong')
            partner_id = self.env['res.users'].browse(line.user_id.id).partner_id
            move = self.env['account.move'].create({
                'journal_id': 3,
                'date': line.date_journal,
                # 'branch_id': line.branch_id.id,
                'ref': line.name,
                'realisasi_id': int(line.id),
            })
            if move:
                move_line = []
                for i in range(1):
                    move_line.append((0, 0, {
                        'account_id': line.source_account.id,
                        # Ganti dengan akun yang sesuai
                        'date': line.date_journal,
                        'name': str(line.name),
                        'partner_id': int(partner_id.id),
                        'debit': 0.0,
                        'credit': line.total_amount,
                    }))
                for lines in line.realisasi_line:
                    move_line.append((0, 0, {
                        'account_id': lines.account_id.id,
                        # Ganti dengan akun yang sesuai
                        'date': line.date_journal,
                        'name': str(line.name) + " " + str(lines.description or ''),
                        'partner_id': int(partner_id.id),
                        'debit': lines.amount,
                        'credit': 0.0,
                    }))
                move.write({
                    'line_ids': move_line
                })
                move.action_post()
                saldo_data = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
                new_saldo = float(saldo_data.saldo) - float(line.total_amount)
                saldo_data.write({
                    'saldo': float(new_saldo)
                })
            self.message_post(body="This document has been posted.")
            line.state = 'posted'

    def action_reset_to_draft(self):
        for line in self:
            saldo = self.env['saldo.dana'].search([('employee_id', '=', int(line.employee_id.id))])
            saldo_update = saldo.saldo + line.total_amount
            saldo.write({'saldo': saldo_update})
            journal = self.env['account.move'].search([('realisasi_id', '=', int(line.id))])
            journal.button_draft()
            journal.unlink()
            line.state = 'draft'

    def default_get(self, fields_list):
        defaults = super(RealisasiDana, self).default_get(fields_list)

        permintaan_id = self.env.context.get('permintaan_id', False)
        saldo = self.env.context.get('saldo', False)
        employee_id = self.env.context.get('employee_id', False)
        source_account = self.env.context.get('source_account', False)

        if permintaan_id and saldo:
            defaults['permintaan_id'] = permintaan_id
            defaults['saldo'] = saldo
            defaults['employee_id'] = employee_id
            defaults['source_account'] = source_account
        return defaults

    @api.depends('realisasi_line.amount')
    def _compute_total_cost(self):
        for line in self:
            cost = 0
            for lines in line.realisasi_line:
                cost += lines.amount
            line.total_amount = cost

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals['total_amount'] > vals['saldo'] for vals in vals_list):
            raise UserError('Saldo Tidak mencukupi')
        if not any(vals['realisasi_line'] for vals in vals_list):
            raise UserError('Silahkan tambahkan item pada line terlebih dahulu')
        # if vals_list.get('total_amount') > vals_list.get('saldo'):
        #     raise UserError('Saldo tidak mencukupi!')
        for value in vals_list:
            for lines in value['realisasi_line']:
                # print(lines[2]['amount'])
                if lines[2]['amount'] <= 0:
                    raise UserError('Amount tidak boleh 0.0')
        # for line in self:
        #     if not line.realisasi_line:
        #         raise UserError('Silahkan tambahkan item pada line terlebih dahulu')
        #     for lines in line.realisasi_line:
        #         if lines.saldo == 0:
        #             raise UserError('Amount tidak boleh 0.0')
        moves = super().create(vals_list)
        moves['name'] = self.env['ir.sequence'].next_by_code('REALISASI')
        a = moves['name']
        index = 2
        department = self.env['hr.department'].search([('id', '=', int(moves['department_id']))])
        if department and department.code:
            code = '-' + str(department.code) or ''
            a = a[:index] + code + a[index:]
        moves['name'] = a

        return moves


class RealisasiLine(models.Model):
    _name = 'realisasi.line'

    date = fields.Date()
    type = fields.Char()
    description = fields.Text()
    amount = fields.Float()
    account_id = fields.Many2one('account.account')
    realisasi_id = fields.Many2one('realisasi.dana')


class RefundDana(models.Model):
    _name = 'refund.dana'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    user_id = fields.Many2one('res.users')
    employee_id = fields.Many2one('hr.employee')
    department_id = fields.Many2one('hr.department')
    dana_id = fields.Many2one('permintaan.dana')
    date = fields.Date(required=True)
    amount = fields.Float()
    source_account = fields.Many2one('account.account')
    dest_account = fields.Many2one('account.account')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')
    ], default='draft')

    def unlink(self):
        for line in self:
            if line.state == 'posted':
                raise UserError('Tidak dapat menghapus dokumen, Status Posted!')
        return super().unlink()

    def action_post(self):
        for line in self:
            if line.source_account and line.dest_account:
                partner_id = self.env['res.users'].browse(line.user_id.id).partner_id
                move = self.env['account.move'].create({
                    'journal_id': 3,
                    'date': line.date,
                    # 'branch_id': line.branch_id.id,
                    'ref': line.name,
                    'refund_id': int(line.id),
                    'line_ids': [
                        (0, 0, {
                            'account_id': line.dest_account.id,
                            # Ganti dengan akun yang sesuai
                            'date': line.date,
                            'name': str(line.name),
                            'partner_id': int(partner_id.id),
                            'debit': line.amount,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'account_id': line.source_account.id,
                            # Ganti dengan akun yang sesuai
                            'date': line.date,
                            'name': str(line.name),
                            'partner_id': int(partner_id.id),
                            'debit': 0.0,
                            'credit': line.amount,
                        }),
                    ],
                })
                saldo_data = self.env['saldo.dana'].search([('employee_id', '=', line.employee_id.id)])
                move.action_post()
                update_saldo = saldo_data.saldo - line.amount
                saldo_data.write({
                    'saldo': float(update_saldo)
                })
                line.state = 'posted'

            self.message_post(body=f"This document has been posted. Refund amount : {str(line.amount)}")

    def action_reset_to_draft(self):
        for line in self:
            saldo = self.env['saldo.dana'].search([('employee_id', '=', int(line.employee_id.id))])
            saldo_update = saldo.saldo + line.amount
            saldo.write({'saldo': saldo_update})
            journal = self.env['account.move'].search([('refund_id', '=', int(line.id))])
            journal.button_draft()
            journal.unlink()
            line.state = 'draft'

    def default_get(self, fields_list):
        defaults = super(RefundDana, self).default_get(fields_list)

        dana_id = self.env.context.get('dana_id', False)
        amount = self.env.context.get('amount', False)
        employee_id = self.env.context.get('employee_id', False)
        department_id = self.env.context.get('department_id', False)
        source_account = self.env.context.get('source_account', False)
        dest_account = self.env.context.get('dest_account', False)

        if dana_id:
            defaults['dana_id'] = dana_id
            defaults['user_id'] = self.env.uid
            defaults['amount'] = amount
            defaults['employee_id'] = employee_id
            defaults['department_id'] = department_id
            defaults['source_account'] = source_account
            defaults['dest_account'] = dest_account
            defaults['date'] = datetime.today()

        return defaults

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves['name'] = self.env['ir.sequence'].next_by_code('REFUND')
        return moves


class SaldoKas(models.Model):
    _name = 'saldo.dana'

    employee_id = fields.Many2one('hr.employee')
    saldo = fields.Float()


class HrDepartmentINh(models.Model):
    _inherit = 'hr.department'

    code = fields.Char()


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    dana_id = fields.Many2one('permintaan.dana')
    realisasi_id = fields.Many2one('realisasi.dana')
    refund_id = fields.Many2one('refund.dana')
    detail_ids = fields.One2many('detail.move.product', 'move_id')
    is_dp = fields.Boolean()
    total_dp = fields.Float(compute="_compute_total_dp")

    def _compute_total_dp(self):
        for line in self:
            detail = self.env['detail.move.product'].search([('move_id', '=', int(line.id))])
            c = 0
            for lines in detail:
                c += detail.subtotal
            line.total_dp = c


class DetailMoveProduct(models.Model):
    _name = 'detail.move.product'

    partner_id = fields.Many2one('res.partner', related="move_id.partner_id")
    product_id = fields.Many2one('product.product')
    currency_id = fields.Many2one('res.currency', related="move_id.currency_id")
    name = fields.Text()
    quantity = fields.Float()
    uom_id = fields.Many2one('uom.uom')
    price_unit = fields.Float()
    discount = fields.Float()
    tax_ids = fields.Many2many('account.tax')
    subtotal = fields.Float(compute="_compute_subtotal")
    move_id = fields.Many2one('account.move')
    tax_base = fields.Monetary(
        string='Tax Base',
        currency_field='currency_id',
        compute="_compute_tax_base",
        store=True,
        help="Calculated tax base as 11/12 of the subtotal."
    )

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_tax_base(self):
        for rec in self:
            rec.tax_base = (11 / 12) * (
                        (rec.quantity * rec.price_unit) - rec.discount) if rec.quantity and rec.price_unit else 0.0

    @api.onchange('product_id')
    def onchange_product(self):
        for line in self:
            line.uom_id = False
            line.tax_ids = False
            line.price_unit = 0
            if line.product_id:
                # raise UserError('test')
                line.uom_id = line.product_id.uom_id.id
                line.price_unit = line.product_id.lst_price
                line.tax_ids = line.product_id.taxes_id
                line.quantity = 1

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_subtotal(self):
        for line in self:
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=False,
                )
                # line.price_subtotal = taxes_res['total_excluded']
                line.subtotal = taxes_res['total_included']
            else:
                line.subtotal = subtotal
