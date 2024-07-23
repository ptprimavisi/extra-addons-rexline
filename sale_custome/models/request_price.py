from odoo import api, fields, models
from odoo.exceptions import UserError


class RequestPrice(models.Model):
    _name = 'request.price'

    inquiry_id = fields.Many2one('inquiry.inquiry')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirm')
    ], default="draft")
    date = fields.Date()
    request_line_ids = fields.One2many('request.price.line', 'request_id')
    request_other_line_ids = fields.One2many('request.price.other.line', 'request_id')
    partner_id = fields.Many2one('res.partner')
    total_price = fields.Float(compute="_total_total_price")
    total_shipment_cost = fields.Float(compute="_total_shipment_cost")
    total_duty = fields.Float()
    total_tax = fields.Float()
    total_duty_tax = fields.Float(compute="_compute_total_pajak")

    @api.depends('request_line_ids.tax', 'request_line_ids.duty')
    def _compute_total_pajak(self):
        for line in self:
            cost = 0
            for lines in line.request_line_ids:
                cost += lines.duty + lines.tax
            line.total_duty_tax = int(cost)

    @api.depends('request_line_ids.cost_price')
    def _total_total_price(self):
        for line in self:
            cost = 0
            for lines in line.request_line_ids:
                cost += lines.cost_price * lines.quantity
            line.total_price = cost

    @api.depends('request_line_ids.shipment_cost')
    def _total_shipment_cost(self):
        for line in self:
            cost = 0
            for lines in line.request_line_ids:
                cost += lines.shipment_cost
            line.total_shipment_cost = cost

    @api.depends('request_line_ids.duty')
    def _total_total_duty(self):
        for line in self:
            cost = 0
            for lines in line.request_line_ids:
                cost += lines.duty
            line.total_duty = cost

    @api.depends('request_line_ids.tax')
    def _total_total_tax(self):
        for line in self:
            cost = 0
            for lines in line.request_line_ids:
                cost += lines.tax
            line.total_tax = cost

    def action_print_report(self):
        for line in self:
            list = []
            for lines in line.request_line_ids:
                list.append({
                    'product': lines.product_id.product_tmpl_id.name,
                    'brand': lines.brand,
                    'weight': lines.weight,
                    'supplier': lines.vendor_id.name,
                    'uom': lines.product_uom.name,
                    'qty': lines.quantity,
                    'cost': lines.cost_price,
                    'subtotal': lines.subtotal,
                })
            data = {
                'inquiry_name': line.inquiry_id.name,
                'date': str(line.date),
                'customer': line.partner_id.name,
                'item_detail': list
            }

            return self.env.ref('sale_custome.action_report_request_price').with_context(
                paperformat=4, landscape=False).report_action(self, data=data)

    def action_other_cost(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Other Cost',
            'res_model': 'price.compute',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        for line in self:
            for lines in line.request_line_ids:
                if lines.product_id:
                    product = self.env['product.product'].search([('id', '=', lines.product_id.id)])
                    if product:
                        if lines.cost_price == 0:
                            raise UserError('Price cannot be 0.0')
                        else:
                            inquiry_line_detail = self.env['inquiry.line.detail'].search(
                                [('inquiry_id', '=', line.inquiry_id.id), ('product_id', '=', int(product.id))])
                            cost = lines.cost_price
                            if lines.other_cost:
                                sesudah_dibagi = lines.other_price / lines.quantity
                                cost = lines.cost_price + sesudah_dibagi
                            # else:

                            inquiry_line_detail.write({'cost_price': cost})
                        # bom = self.env['mrp.bom'].search([('id', '=', int(line.bom_id.id))])
                        # bom.write({
                        #     'request_state': False
                        # })
                        rp = self.env['request.price'].search([('id', '=', int(line.id))])
                        rp.write({'state': 'posted'})
                    else:
                        raise UserError('Product is empty')
                else:
                    raise UserError('Product is empty')


class RequestPriceLine(models.Model):
    _name = "request.price.line"

    product_id = fields.Many2one('product.product')
    description = fields.Text()
    brand = fields.Char()
    cost_price = fields.Float()
    weight = fields.Float()
    shipment_cost = fields.Float()
    duty = fields.Float()
    tax = fields.Float()
    other_cost = fields.Many2many('other.price.line')
    other_price = fields.Float()
    show_other_price = fields.Boolean(compute="_compute_show")
    product_uom = fields.Many2one('uom.uom', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    request_id = fields.Many2one('request.price')
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier_rank', '!=', 0)]")
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals',
        # currency_field=None,
    )
    percentage = fields.Float(compute="_compute_percentage")
    total_price = fields.Float(compute="_compute_total_price")
    final_cost = fields.Float(compute="_compute_final")

    @api.depends('total_price', 'shipment_cost')
    def _compute_final(self):
        for line in self:
            cost = line.total_price + (line.shipment_cost + line.duty + line.tax)
            cost = cost / line.quantity
            line.final_cost = round(cost)

    @api.depends('cost_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.cost_price * line.quantity

    @api.depends('cost_price')
    def _compute_percentage(self):
        for line in self:
            total = line.request_id.total_price
            cost = line.total_price / total
            line.percentage = round(cost * 100)

    @api.depends('other_cost')
    def _compute_show(self):
        for line in self:
            line.show_other_price = False
            if line.other_cost:
                line.show_other_price = True

    @api.depends('quantity', 'final_cost', 'other_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line.final_cost
            if line.other_price:
                subtotal = subtotal + line.other_price
            else:
                line.subtotal = subtotal


class RequestPriceOtherLine(models.Model):
    _name = "request.price.other.line"

    item_id = fields.Many2one('other.price.line')
    description = fields.Char()
    amount = fields.Float()
    request_id = fields.Many2one('request.price')


class OtherPriceLine(models.Model):
    _name = "other.price.line"

    name = fields.Char()
    description = fields.Text()
