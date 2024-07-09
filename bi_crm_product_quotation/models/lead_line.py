from odoo import api, fields, models, _

class lead_line(models.Model):
    _name = 'lead.line'
    _description = "Lead Line"

    lead_line_id = fields.Many2one('crm.lead',string ="crm")
    product_id = fields.Many2one('product.product', string='Product',required = True)
    name = fields.Text(string='Description', required = True)
    product_uom_quantity = fields.Float(string='Order Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    margin = fields.Selection([
        ('0', '0 %'),
        ('10', '10 %'),
        ('20', '20 %'),
        ('30', '30 %'),
        ('40', '40 %'),
        ('50', '50 %'),
        ('60', '60 %'),
        ('70', '70 %'),
        ('80', '80 %'),
        ('90', '90 %'),
        ('100', '100 %'),

    ])
    cost_price = fields.Float('Cost Price', default=0.0)
    price_unit = fields.Float('Unit Price', default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')

    @api.onchange('margin')
    def action_margin(self):
        for line in self:
            line.price_unit = False
            if line.margin:
                margin = int(line.margin)
                persentase = line.cost_price * margin
                fix_margin = persentase / 100
                line.price_unit = line.cost_price + fix_margin

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.write({
                        'name'                      : self.product_id.name,
                        'price_unit'                : self.product_id.lst_price,
                        'product_uom'               : self.product_id.uom_id.id,
                        'tax_id'                    : self.product_id.taxes_id or False
                      })

class lead_line_detail(models.Model):
    _name = 'lead.line.detail'
    _description = "Lead Line Detail"

    lead_line_id = fields.Many2one('crm.lead', string="crm")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Text(string='Description', required=True)
    product_uom_quantity = fields.Float(string='Order Quantity', digits='Product Unit of Measure', required=True,
                                        default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    cost_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals', store=True,
        # currency_field=None,
    )

    @api.depends('product_uom_quantity', 'cost_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.product_uom_quantity * line.cost_price
            line.subtotal = subtotal




