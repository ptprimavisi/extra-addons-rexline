from odoo import api, fields, models
from odoo.exceptions import UserError


class QuotationCount(models.TransientModel):
    _name = "count.quotation"

    product_id = fields.Many2one('product.product')
    count_line = fields.One2many('count.quotation.line', 'count_id')

    def action_cancel(self):
        pass

    def default_get(self, fields_list):
        defaults = super(QuotationCount, self).default_get(fields_list)
        product_id = self.env.context.get('product_id', False)
        count_line = self.env.context.get('count_line', False)
        if product_id and count_line:
            defaults['product_id'] = product_id
            defaults['count_line'] = count_line
        return defaults

class QuotationLine(models.TransientModel):
    _name = "count.quotation.line"

    count_id = fields.Many2one('count.quotation')
    vendor_id = fields.Many2one('res.partner')
    price_unit = fields.Float()
    quantity = fields.Float()
    subtotal = fields.Float(compute="compute_subtotal")

    @api.depends('quantity', 'price_unit')
    def compute_subtotal(self):
        for line in self:
            line.subtotal = 0.0
            if line.quantity and line.price_unit:
                line.subtotal = line.price_unit * line.quantity
