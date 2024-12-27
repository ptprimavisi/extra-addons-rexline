from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductionReport(models.Model):
    _name = 'production.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    mo_id = fields.Many2one('mrp.production')
    name = fields.Char()
    product_id = fields.Many2one('product.product')
    activity_date = fields.Date()
    note = fields.Text()
    production_line_ids = fields.One2many('production.report.line', 'production_id')
    mrf_ids = fields.Many2many('mrf.mrf', compute="_compute_mrf_ids")
    inquiry_id = fields.Many2one('inquiry.inquiry')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default="draft")
    count_sk = fields.Integer(compute="_compute_count_sk")
    count_report = fields.Integer(compute="_compute_count_report")

    def _compute_count_report(self):
        count = 0
        report = self.env['general.daily.report'].search([('schedule_id', '=', int(self.id))])
        if report:
            for lines in report:
                count += 1
        self.count_report = count

    def action_count_report(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "general.daily.report",
            "domain": [('schedule_id', '=', int(self.id))],
            "context": {"create": False},
            "name": "Report",
            'view_mode': 'tree,form',
        }

    def action_report(self):
        for line in self:
            #
            inquiry_ids = []
            if line.mrf_ids:
                for lines in line.mrf_ids:
                    if lines.inquiry_id:
                        inquiry_ids.append(lines.inquiry_id.id)

            inquiry = self.env['inquiry.inquiry'].search([('id', 'in', inquiry_ids)])

            so = self.env['sale.order'].search(
                [('opportunity_id', '=', inquiry.opportunity_id.id),
                 ('state', '=', 'sale'),
                 ('opportunity_id', '!=', False)])
            # raise UserError(so)
            list_employee = []
            sk = self.env['surat.kerja'].search([('progres_id', '=', int(line.id))])
            sk_line = self.env['surat.kerja.line'].search([('sk_id', 'in', sk.ids)])
            # raise UserError(sk_line)
            for line_employee in sk_line:
                if not any(line_employee.employee_id.id == item[2]['employee_id'] for item in list_employee):
                    list_employee.append((0, 0, {
                        'employee_id': line_employee.employee_id.id
                    }))
            return {
                'type': 'ir.actions.act_window',
                'name': 'Generate Report',
                'res_model': 'general.daily.report',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_partner_id': int(inquiry.partner_id.id) or False,
                    'default_schedule_id': int(line.id),
                    'default_date': str(line.activity_date),
                    'default_sale_id': int(so.id) or False,
                    'default_man_power_ids': list_employee
                }
                # 'request_line_ids': list
            }

    # @api.depends('id')
    def _compute_count_sk(self):
        for line in self:
            count = 0
            sk = self.env['surat.kerja'].search([('progres_id', '=', int(line.id))])
            # raise UserError(len(sk))
            if sk:
                for lines in sk:
                    count += 1
            line.count_sk = len(sk)

    def action_count_sk(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "surat.kerja",
            "domain": [('progres_id', '=', int(self.id))],
            "context": {"create": False},
            "name": "Surat Kerja",
            'view_mode': 'tree,form',
        }

    @api.depends('mo_id')
    def _compute_mrf_ids(self):
        for record in self:
            mo = self.env['mrp.production'].browse(record.mo_id.id)
            # raise UserError(mo)
            if mo:
                if mo.origin:
                    sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                    if sale:
                        mrf = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                        if mrf:
                            record.mrf_ids = mrf.ids
                        else:
                            record.mrf_ids = False
                        # raise UserError(mrf.ids)
                    else:
                        mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                        if mo.origin:
                            sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                            if sale:
                                mrf = self.env['mrf.mrf'].search(
                                    [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                                if mrf:
                                    record.mrf_ids = mrf.ids
                                else:
                                    record.mrf_ids = False
                            else:
                                mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                                if mo.origin:
                                    sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                                    if sale:
                                        mrf = self.env['mrf.mrf'].search(
                                            [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                                        if mrf:
                                            record.mrf_ids = mrf.ids
                                        else:
                                            record.mrf_ids = False
                                    else:
                                        mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                                        if mo.origin:
                                            sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                                            if sale:
                                                mrf = self.env['mrf.mrf'].search(
                                                    [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                                                if mrf:
                                                    record.mrf_ids = mrf.ids
                                                else:
                                                    record.mrf_ids = False
                                            else:
                                                mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                                                if mo.origin:
                                                    sale = self.env['sale.order'].search(
                                                        [('name', '=', str(mo.origin))])
                                                    if sale:
                                                        mrf = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id',
                                                                                           '=',
                                                                                           sale.opportunity_id.id)])
                                                        if mrf:
                                                            record.mrf_ids = mrf.ids
                                                        else:
                                                            record.mrf_ids = False
                else:
                    record.mrf_ids = False
            else:
                record.mrf_ids = False
            # mrf_records = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id', '=', record.mo_id.opportunity_id.id)])
            # record.mrf_ids = mrf_records

    def action_confirm(self):
        for line in self:
            line.state = 'done'
            if line.mo_id:
                line.mo_id.action_compute_consume()

    def action_rest_draft(self):
        for line in self:
            line.state = 'draft'
            if line.mo_id:
                line.mo_id.action_compute_consume()

    def action_create_sk(self):
        for line in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create SK',
                'res_model': 'surat.kerja',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'progres_id': int(line.id),
                }
            }

    def default_get(self, fields_list):
        defaults = super(ProductionReport, self).default_get(fields_list)

        product_id = self.env.context.get('product_id', False)
        production_line_ids = self.env.context.get('production_line_ids', False)
        mo_id = self.env.context.get('mo_id', False)
        if product_id:
            defaults['mo_id'] = mo_id
            defaults['product_id'] = product_id
            defaults['production_line_ids'] = production_line_ids
        return defaults


class ProductionReportLine(models.Model):
    _name = 'production.report.line'

    product_id = fields.Many2one('product.product')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], related='production_id.state')
    qty_consume = fields.Float()
    qty_to_consume = fields.Float(compute="_compute_to_consume", readonly=False)
    weight = fields.Integer()
    production_id = fields.Many2one('production.report')
    raw_id = fields.Many2one('stock.move')

    def _compute_to_consume(self):
        for line in self:
            # material = self.env['stock.move'].search([('raw_material_production_id', '=', line.production_id.mo_id.id), ('product_id', '=', )])
            # line.qty_to_consume = 0.0
            material = line.production_id.mo_id.move_raw_ids

            materials = self.env['stock.move'].search(
                [('raw_material_production_id', '=', line.production_id.mo_id.id),
                 ('id', '=', line.raw_id.id)])
            if materials:
                schedule_done = self.env['production.report.line'].search(
                    [('raw_id', '=', materials.id), ('production_id.state', '=', 'done')])
                line.qty_to_consume = materials.product_uom_qty - sum(schedule_done.mapped('qty_consume'))


class ProductionTag(models.Model):
    _name = 'production.tag'

    name = fields.Char()
