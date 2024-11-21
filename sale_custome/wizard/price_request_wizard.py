from odoo import api, fields, models
from odoo.exceptions import UserError
import math


#
#
class RequestPriceWizard(models.TransientModel):
    _name = 'request.price.wizard'

    inquiry_id = fields.Many2one('inquiry.inquiry')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirm')
    ], default="draft")
    date = fields.Date()
    project_category = fields.Selection([
        ('project', 'Project'),
        ('service', 'Service'),
        ('supply', 'Supply')
    ])
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'request.price.wizard')],
        string='Attachments'
    )
    request_line_ids = fields.One2many('request.price.line.wizard', 'request_id')

    def default_get(self, vals):
        defaults = super(RequestPriceWizard, self).default_get(vals)

        inquiry_id = self.env.context.get('inquiry_id', False)
        date = self.env.context.get('date', False)
        request_line_ids = self.env.context.get('request_line_ids', False)
        # raise UserError(partner_id)
        if inquiry_id:
            defaults['inquiry_id'] = inquiry_id
            defaults['date'] = date
            defaults['request_line_ids'] = request_line_ids

        return defaults

    def process_attachments(self):
        for record in self:
            attachments = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', record.id)])
            return attachments

    def action_save(self):
        for line in self:
            if line.inquiry_id:

                request_price = self.env['request.price'].search([])
                list_product = []
                for lines in line.request_line_ids:
                    list_product.append((0, 0, {
                        'product_id': lines.product_id.id,
                        'description': lines.description,
                        'quantity': lines.quantity,
                        'product_uom': lines.product_uom.id,
                        'weight': float(lines.weight),
                        'cost_price': lines.cost_price
                    }))
                attachment_data = []

                # raise UserError(line.attachment_ids)
                # if not attachment_data:
                #     raise UserError("No attachments found for this record.")
                data = {
                    'inquiry_id': line.inquiry_id.id,
                    'date': line.date,
                    'project_category': line.project_category,
                    'partner_id': line.inquiry_id.opportunity_id.partner_id.id,
                    'request_line_ids': list_product,
                }
                req = self.env['request.price'].create(data)
                for attachment in line.attachment_ids:
                    attachment = {
                        'name': attachment.name,
                        'datas': attachment.datas,  # Binary data attachment
                        # 'datas_fname': attch_line.datas_fname,  # File name of attachment
                        'res_model': 'request.price',  # Model name of sale.order
                        'res_id': int(req.id),
                        'type': 'binary',
                    }
                    self.env['ir.attachment'].create(attachment)
                request = self.env['inquiry.inquiry'].browse(int(line.inquiry_id.id))
                # raise UserError(bom)
                request.write({'state': 'request'})
            else:
                raise UserError('Inquiry has been deleted')
        # pass

    # def action_confirm(self):
    #     for line in self:
    #         for lines in line.request_line_ids:
    #             if lines.product_id:
    #                 product = self.env['product.product'].search([('id', '=', lines.product_id.id)])
    #                 if product:
    #                     if lines.cost_price == 0:
    #                         raise UserError('Price cannot be 0.0')
    #                     else:
    #                         product_tmpl = self.env['product.template'].search(
    #                             [('id', '=', product.product_tmpl_id.id)])
    #                         product_tmpl.write({'standard_price': lines.cost_price})
    #                     # bom = self.env['mrp.bom'].search([('id', '=', int(line.bom_id.id))])
    #                     # bom.write({
    #                     #     'request_state': False
    #                     # })
    #                     rp = self.env['request.price'].search([('id', '=', int(line.id))])
    #                     rp.write({'state': 'posted'})
    #                 else:
    #                     raise UserError('Product is empty')
    #             else:
    #                 raise UserError('Product is empty')


#
#
class RequestPriceLineWizard(models.TransientModel):
    _name = "request.price.line.wizard"

    product_id = fields.Many2one('product.product')
    description = fields.Text()
    brand = fields.Char()
    cost_price = fields.Float()
    weight = fields.Float()
    product_uom = fields.Many2one('uom.uom')
    request_id = fields.Many2one('request.price.wizard')
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier_rank', '!=', 0)]")
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals', store=True,
        # currency_field=None,
    )

    @api.depends('quantity', 'cost_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line.cost_price
            line.subtotal = subtotal


#

class PriceComputation(models.TransientModel):
    _name = 'price.compute'

    shipment_cost = fields.Float()
    fob_cost = fields.Float()
    duty = fields.Float()
    vat = fields.Float()
    tax = fields.Float()

    def action_compute(self):
        for line in self:
            active_id = self.env.context.get('active_id')
            request_price = self.env['request.price'].browse(int(active_id))
            if request_price:
                if request_price.total_price == 0:
                    raise UserError('cost price caanot be empty')
                duty_total = (line.duty / 100) * (
                        request_price.total_price + (0.10 * request_price.total_price) + (
                        0.005 * (request_price.total_price + (0.10 * request_price.total_price)))) or 0
                tax_total = (line.tax / 100) * (request_price.total_price + (
                            request_price.total_price + (0.1 * request_price.total_price) + (0.005 * (
                                request_price.total_price + (
                                    0.1 * request_price.total_price)))) + request_price.total_duty)
                # CEILING((L15 * (I22 + (I22 + (10 % * I22) + (0.5 % * (I22 + (10 % * I22)))) + L22)), 1000)
                # raise UserError(request_price.total_price)
                # (L14*(I22+(I22+(10%*I22)+(0.5%*(I22+(10%*I22))))+L22))

                total_vat = ((line.vat / 100) * (request_price.total_price + (
                            request_price.total_price + (0.1 * request_price.total_price) + (
                                0.005 * (request_price.total_price + (0.1 * request_price.total_price)))) + duty_total))
                # raise UserError(total_vat)
                request_price.write({
                    'total_duty': duty_total,
                    'total_tax': math.ceil(tax_total / 1000) * 1000,
                    'total_vat': math.ceil(total_vat / 1000) * 1000,
                    'total_delivery': line.fob_cost
                })
                request_line = self.env['request.price.line'].search([('request_id', '=', int(request_price.id))])
                for lines in request_line:
                    line_req = self.env['request.price.line'].browse(lines.id)
                    persen = line_req.total_price / line_req.request_id.total_price
                    duty = persen * request_price.total_duty
                    cost = persen * line.shipment_cost
                    tax = persen * request_price.total_tax
                    vat = persen * request_price.total_vat
                    fob = persen * line.fob_cost
                    line_req.write({
                        'shipment_cost': cost,
                        'duty': duty,
                        'tax': int(tax),
                        'vat': vat,
                        'fob': fob
                    })
