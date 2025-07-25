from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class RfqWizard(models.Model):
    _name = 'rfq.wizard'

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    due_date = fields.Date()
    rfq_line_ids = fields.One2many('rfq.wizard.line', 'rfq_id')
    inquiry_id = fields.Many2one('inquiry.inquiry', default=lambda self: self.env.context.get('active_ids', [])[0])
    sale_id = fields.Many2one('sale.order')
    validity = fields.Datetime()
    lead_time = fields.Datetime()
    picking_type_id = fields.Many2one('stock.picking.type', domain="[('code','=','incoming')]")

    # state = fields.Selection([
    #     ('rfp', 'Request for Price'),
    #     ('boq', 'Cost Estimation'),
    #     ('mrf', 'MRF')
    # ], default='rfp')

    def button_save(self):
        for line in self:
            mrf = self.env['mrf.mrf'].search([])
            line_list = []
            inquiry = self.env['inquiry.inquiry'].browse(int(line.inquiry_id.id))
            inquiry.write({'state': 'done'})
            for lines in line.rfq_line_ids.filtered(lambda l: isinstance(l.id, int)):
                qty_purchase = 0
                if lines.quantity or lines.available_qty:
                    total = lines.quantity - lines.available_qty
                    if lines.quantity < lines.available_qty:
                        total = 0.0
                    qty_purchase = total
                line_list.append((0, 0, {
                    "product_id": int(lines.product_id.id),
                    "type": str(lines.type),
                    "description": lines.description,
                    "specs_detail": lines.specs_detail,
                    "brand": lines.brand,
                    'unit_weight': lines.unit_weight,
                    "quantity": lines.quantity,
                    "qty_purchase": qty_purchase,
                    "product_uom_id": lines.product_uom.id,
                    "budget": float(int(lines.budget)),
                    "unit_cost": float(lines.unit_cost),
                    "wh_id": int(lines.wh_id.id),
                    "schedule_date": lines.schedule_date,
                    "sale_id": int(line.sale_id.id),
                    "avilable_qty": lines.available_qty,
                    'attachment': lines.attachment
                }))
            # print(line_list)
            # exit()
            data = {
                # "name": self.env['ir.sequence'].next_by_code('RFQ'),
                'state': 'to_inventory',
                "partner_id": line.partner_id.id,
                "request_date": datetime.now(),
                'due_date': str(line.due_date),
                'validity': str(line.validity),
                'lead_time': str(line.lead_time),
                "inquiry_id": line.inquiry_id.id,
                "picking_type_id": line.picking_type_id.id,
                "mrf_line_ids": line_list
            }
            mrf.create(data)

    def _compute_inquiry(self):
        for line in self:
            active_ids = self.env.context.get('active_ids', [])
            # raise UserError(active_ids)
            # active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                return active_ids[0]
            else:
                return False

    def default_get(self, vals):
        defaults = super(RfqWizard, self).default_get(vals)

        # Pastikan Anda memiliki konteks yang menyediakan partner_id
        partner_id = self.env.context.get('partner_id', False)
        inquiry_id = self.env.context.get('inquiry_id', False)
        sale_id = self.env.context.get('sale_id', False)
        due_date = self.env.context.get('due_date', False)
        rfq_line_ids = self.env.context.get('rfq_line_ids', False)
        # raise UserError(partner_id)
        if partner_id:
            defaults['partner_id'] = partner_id
            defaults['inquiry_id'] = inquiry_id
            defaults['sale_id'] = sale_id
            defaults['due_date'] = due_date
            defaults['rfq_line_ids'] = rfq_line_ids

        return defaults


class RfqLine(models.Model):
    _name = 'rfq.wizard.line'

    product_id = fields.Many2one('product.product')
    type = fields.Char()
    description = fields.Char()
    specs_detail = fields.Char()
    brand = fields.Char()
    quantity = fields.Float(default=1)
    available_qty = fields.Float(compute="_compute_available_qty", store=True, readonly=False, precompute=True)
    qty_purchase = fields.Float()
    product_uom = fields.Many2one('uom.uom')
    unit_weight = fields.Float()
    total_weight = fields.Float(compute="_compute_weight")
    unit_cost = fields.Float()
    subtotal = fields.Float(compute="_compute_subtotal")
    budget = fields.Float()
    rfq_id = fields.Many2one('rfq.wizard')
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_name = fields.Char(string='Attachment Name')
    schedule_date = fields.Date(default= lambda self: self.rfq_id.due_date)
    wh_id = fields.Many2one('stock.warehouse', domain=lambda self: [('company_id', '=', self.env['res.users'].browse(self.env.uid).company_id.id)],
                            default=lambda self: self.env['stock.warehouse'].search(
                                [('company_id', '=', self.env['res.users'].browse(self.env.uid).company_id.id)],
                                limit=1).id)

    @api.onchange('product_id')
    def action_product(self):
        for line in self:
            line.unit_cost = False
            line.unit_weight = False
            if line.product_id:
                line.unit_cost = line.product_id.product_tmpl_id.standard_price
                line.unit_weight = line.product_id.product_tmpl_id.weight

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            subtotal = line.quantity * line.unit_cost
            line.subtotal = subtotal

    @api.depends('quantity', 'unit_weight')
    def _compute_weight(self):
        for line in self:
            total = line.quantity * line.unit_weight
            line.total_weight = total

    @api.depends('product_id')
    def _compute_available_qty(self):
        for line in self:
            line.available_qty = 0.0
            # raise UserError(line.product_id.id)
            if line.product_id:
                stock_quant = self.env['stock.quant'].with_context(inventory_mode=True).search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', 8)])
                total_quantity = sum(stock_quant.mapped('quantity'))
                # line.avilable_qty = total_quantity
                if stock_quant:
                    line.available_qty = float(stock_quant.available_quantity)


class SheduleWizard(models.TransientModel):
    _name = 'schedule.wizard'

    id_mo = fields.Many2one('mrp.production')
    date_from = fields.Date()
    date_to = fields.Date()

    def button_save(self):
        for line in self:
            start = line.date_from
            end = line.date_to
            if start > end:
                raise UserError('Start Date tidak boleh melebihi end Date')
            num_days = (end - start).days
            pr = self.env['production.report'].search([])
            mo_id = self.env.context.get('mo_id', False)
            product_id = self.env.context.get('product_id', False)
            production_line_ids = self.env.context.get('production_line_ids', False)
            # raise UserError(start)
            for days in range(num_days + 1):
                dates = start + timedelta(days=days)
                # datess = datetime.strptime(str(dates), '%Y-%m-%d')
                pr.create({
                    'name' : str(self.env['mrp.production'].browse(self.env.context.get('mo_id')).name) + str("/Progres "+str(days + 1)+"  ("+str(dates)+")"),
                    'mo_id': int(mo_id),
                    'product_id': int(product_id),
                    'activity_date': str(dates),
                    'production_line_ids': production_line_ids
                })
                # print(start + timedelta(days=days))
