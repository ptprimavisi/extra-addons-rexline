from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ManufacturWizard(models.TransientModel):
    _name = 'manufactur.wizard'

    product_id = fields.Many2one('product.product')
    schedule_date = fields.Datetime()
    product_qty = fields.Float()
    warehouse_id = fields.Many2one('stock.warehouse')
    origin = fields.Char()

    def default_get(self, fields_list):
        defaults = super(ManufacturWizard, self).default_get(fields_list)

        product_id = self.env.context.get('product_id', False)
        Schedule_date = self.env.context.get('schedule_date', False)
        product_qty = self.env.context.get('product_qty', False)
        origin = self.env.context.get('origin', False)
        if product_id:
            defaults['product_id'] = product_id
            defaults['schedule_date'] = Schedule_date
            defaults['product_qty'] = product_qty
            defaults['origin'] = origin

        return defaults

    def action_save(self):
        for line in self:
            mo = self.env['mrp.production'].search([])
            picking_type = self.env['stock.picking.type'].search([('warehouse_id','=',line.warehouse_id.id),('code','=','mrp_operation')])
            create_mo = mo.create({
                'product_id': int(line.product_id.id),
                'product_qty': line.product_qty,
                'origin': str(line.origin),
                'picking_type_id': picking_type.id,
                'state': 'draft'
            })
            if create_mo:
                create_mo.action_confirm()
            if create_mo:
                inquiry_id = self.env.context.get('inquiry_id', False)
                inquiry = self.env['inquiry.inquiry'].search([('id','=',int(inquiry_id))])
                if inquiry:
                    inquiry.action_compute_task()


class GeneralDailyReport(models.TransientModel):
    _name = 'general.daily.report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'general.daily.report')],
        string='Attachments'
    )
    schedule_id = fields.Many2one('production.report')
    partner_id = fields.Many2one('res.partner')
    sale_id = fields.Many2one('sale.order')
    location = fields.Char()
    date = fields.Date()
    man_power_ids = fields.One2many('man.power.line', 'report_id')
    problem_ids = fields.One2many('problem.line', 'report_id')
    solving_ids = fields.One2many('solving.line', 'report_id')
    target_ids = fields.One2many('target.line', 'report_id')

    def action_print(self):
        for line in self:
            # raise UserError(line.tax_list)
            return self.env.ref('sale_custome.action_report_daily_report').with_context(
                paperformat=4, landscape=False).report_action(self)


class ManPower(models.TransientModel):
    _name = 'man.power.line'

    employee_id = fields.Many2one('hr.employee')
    description = fields.Many2many('production.tag')
    position = fields.Many2one('hr.job')
    work_hours = fields.Float()
    p = fields.Float()
    t = fields.Float()
    l = fields.Float()
    quantity = fields.Float()
    report_id = fields.Many2one('general.daily.report')

    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            line.position = False
            if line.employee_id:
                if line.employee_id.job_id:
                    line.position = line.employee_id.job_id.id


class ProblemLine(models.TransientModel):
    _name = 'problem.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')


class SolvingLine(models.TransientModel):
    _name = 'solving.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')


class TargetLine(models.TransientModel):
    _name = 'target.line'

    description = fields.Text()
    report_id = fields.Many2one('general.daily.report')
