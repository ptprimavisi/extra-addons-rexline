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

    def action_print_report(self):
        for line in self:
            list = []
            for lines in line.request_line_ids:
                list.append({
                    'product': lines.product_id.product_tmpl_id.name,
                    'Brand': lines.brand,
                    'Weight': lines.weight,
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
        compute='_compute_totals', store=True,
        # currency_field=None,
    )

    @api.depends('other_cost')
    def _compute_show(self):
        for line in self:
            line.show_other_price = False
            if line.other_cost:
                line.show_other_price = True

    @api.depends('quantity', 'cost_price', 'other_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line.cost_price
            if line.other_price:
                line.subtotal = subtotal + line.other_price
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



