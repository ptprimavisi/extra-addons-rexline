# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class InquiryEstimate(models.Model):
    _name = 'inquiry.estimate'

    name = fields.Char()
    sale_id = fields.Many2one('sale.order')
    date = fields.Date()
    category = fields.Char()
    due_date = fields.Date()
    partner_id = fields.Many2one('res.partner')
    estimate_line = fields.One2many('estimate.line', 'estimate_id')
    estimate_line_detail = fields.One2many('estimate.line.detail', 'estimate_id')

    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('EST') or '/'
        return super(InquiryEstimate, self).create(vals)


class EstimateLine(models.Model):
    _name = 'estimate.line'

    estimate_id = fields.Many2one('inquiry.estimate')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Text(string='Description', required=True)
    product_uom_quantity = fields.Float(string='Order Quantity', digits='Product Unit of Measure', required=True,
                                        default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    margin = fields.Float()
    cost_price = fields.Float('Cost Price', default=0.0)
    price_unit = fields.Float('Unit Price', default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    is_under = fields.Boolean()


class EstimateLine(models.Model):
    _name = 'estimate.line.detail'

    estimate_id = fields.Many2one('inquiry.estimate')
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


class crm_lead(models.Model):
    _inherit = 'crm.lead'

    lead_product_ids = fields.One2many('lead.line', 'lead_line_id', string='Products', copy=True)
    lead_product_detail = fields.One2many('lead.line.detail', 'lead_line_id', string="Product Detail", copy=True)
    crm_count = fields.Integer(string="Quotation", compute="get_quotation_count")
    note_header = fields.Text()
    category_project = fields.Selection([
        ('project', 'Project'),
        ('service', 'Service'),
        ('supply', 'Supply')
    ])
    is_crm_quotation = fields.Boolean('Is CRM Quotation')

    def action_quotations_view(self):
        order_line = []
        lines_data = []
        lines_detail = []
        if not self.is_approve:
            raise UserError('Dokumen belum di approve oleh sales technical')
        for record in self.lead_product_ids:
            order_line.append((0, 0, {
                'product_id': record.product_id.id,
                'name': record.name,
                'product_uom_qty': record.product_uom_quantity,
                'price_unit': record.price_unit,
                'tax_id': [(6, 0, record.tax_id.ids)],
            }))
            lines_data.append((0,0, {
                    'product_id': record.product_id.id,
                    'name': record.name,
                    'product_uom_quantity': record.product_uom_quantity,
                    'product_uom_category_id': record.product_uom_category_id.id,
                    'margin': record.margin,
                    'cost_price': record.cost_price,
                    'price_unit': record.price_unit,
                    'tax_id': [(6, 0, record.tax_id.ids)],
                    'is_under': record.is_under
            }))
        for records in self.lead_product_detail:
            lines_detail.append((0,0, {
                'product_id':records.product_id.id,
                'name':records.name,
                'product_uom_quantity':records.product_uom_quantity,
                'product_uom':records.product_uom.id,
                'product_uom_category_id':records.product_uom_category_id.id,
                'cost_price':records.cost_price
            }))
        sale_obj = self.env['sale.order']
        if self.partner_id:
            for record in self.lead_product_ids:
                if record.product_id and record.name:
                    sale_create_obj = sale_obj.create({
                        'partner_id': self.partner_id.id,
                        'opportunity_id': self.id,
                        'state': "draft",
                        'order_line': order_line,
                    })
                    # raise UserError(sale_create_obj)
                    estimate = self.env['inquiry.estimate'].search([])
                    estimate.create({
                        'sale_id': int(sale_create_obj.id),
                        'date' : datetime.now(),
                        'category': self.category_project,
                        'due_date': self.date_deadline,
                        'partner_id':self.partner_id.id,
                        'estimate_line':lines_data,
                        'estimate_line_detail':lines_detail
                    })

                return {
                    'name': "Sale Order",
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'view_id': self.env.ref('sale.view_order_form').id,
                    'target': "new",
                    'res_id': sale_create_obj.id
                }
            else:
                raise UserError('Enter the "Product" and "Description".')
        else:
            raise UserError('Please select the "Customer".')

    def open_quotation_from_view_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['domain'] = [('partner_id', '=', self.partner_id.id), ('opportunity_id', '=', self.id)]
        return action

    def get_quotation_count(self):
        count = self.env['sale.order'].search_count(
            [('partner_id', '=', self.partner_id.id), ('opportunity_id', '=', self.id)])
        self.crm_count = count
