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

    @api.depends('mo_id')
    def _compute_mrf_ids(self):
        for record in self:
            mo = self.env['mrp.production'].browse(record.mo_id.id)
            if mo.origin:
                sale = self.env['sale.order'].search([('name','=', str(mo.origin))])
                if sale:
                    mrf = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                    record.mrf_ids = mrf
                else:
                    mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                    if mo.origin:
                        sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                        if sale:
                            mrf = self.env['mrf.mrf'].search(
                                [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                            record.mrf_ids = mrf
                        else:
                            mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                            if mo.origin:
                                sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                                if sale:
                                    mrf = self.env['mrf.mrf'].search(
                                        [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                                    record.mrf_ids = mrf
                                else:
                                    mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                                    if mo.origin:
                                        sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                                        if sale:
                                            mrf = self.env['mrf.mrf'].search(
                                                [('inquiry_id.opportunity_id', '=', sale.opportunity_id.id)])
                                            record.mrf_ids = mrf
                                        else:
                                            mo = self.env['mrp.production'].search([('name', '=', str(mo.origin))])
                                            if mo.origin:
                                                sale = self.env['sale.order'].search([('name', '=', str(mo.origin))])
                                                if sale:
                                                    mrf = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id','=', sale.opportunity_id.id)])
                                                    record.mrf_ids = mrf

            # mrf_records = self.env['mrf.mrf'].search([('inquiry_id.opportunity_id', '=', record.mo_id.opportunity_id.id)])
            # record.mrf_ids = mrf_records

    def action_confirm(self):
        for line in self:
            line.state = 'done'

    def action_rest_draft(self):
        for line in self:
            line.state = 'draft'

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

    def _compute_to_consume(self):
        for line in self:
            # material = self.env['stock.move'].search([('raw_material_production_id', '=', line.production_id.mo_id.id), ('product_id', '=', )])
            # line.qty_to_consume = 0.0
            material = line.production_id.mo_id.move_raw_ids
            schedule_done = self.env['production.report.line'].search(
                [('production_id.mo_id', '=', line.production_id.mo_id.id), ('production_id.state', '=', 'done'),
                 ('product_id', '=', line.product_id.id)])
            if material:
                materials = self.env['stock.move'].search(
                    [('raw_material_production_id', '=', line.production_id.mo_id.id),
                     ('product_id', '=', line.product_id.id)])
                line.qty_to_consume = materials.product_uom_qty - sum(schedule_done.mapped('qty_consume'))
