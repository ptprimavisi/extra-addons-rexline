# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api


class ShProductTemplate(models.Model):
    _inherit = 'product.template'

    sh_bundle_product_ids = fields.One2many(
        comodel_name='sh.product.bundle',
        inverse_name='sh_bundle_id',
        string="Bundle Line",copy=True, auto_join=True)
    sh_is_bundle = fields.Boolean('Is Bundled ?')
    sh_amount_total = fields.Monetary(
        string='Total', store=True, readonly=True, compute='_amount_all')

    @api.depends('sh_bundle_product_ids.sh_price_subtotal')
    def _amount_all(self):
        amount_total = 0.0
        for order in self:
            if order.sh_bundle_product_ids:
                for line in order.sh_bundle_product_ids:
                    amount_total += line.sh_price_subtotal
                order.sh_amount_total = amount_total

    def compute_bundle_price(self):
        list_price = 0.0
        if self.sh_bundle_product_ids:
            for bundle_product in self.sh_bundle_product_ids:
                list_price += bundle_product.sh_price_subtotal
        self.list_price = list_price

    def compute_bundle_cost_price(self):
        standard_price = 0.0
        if self.sh_bundle_product_ids:
            for bundle_product in self.sh_bundle_product_ids:
                standard_price += (bundle_product.sh_cost_price *
                                   bundle_product.sh_qty)
        self.standard_price = standard_price


class Product(models.Model):
    _inherit = 'product.product'

    def compute_bundle_price(self):
        lst_price = 0.0
        if self.sh_bundle_product_ids:
            for bundle_product in self.sh_bundle_product_ids:
                lst_price += bundle_product.sh_price_subtotal
        self.lst_price = lst_price

    def compute_bundle_cost_price(self):
        standard_price = 0.0
        if self.sh_bundle_product_ids:
            for bundle_product in self.sh_bundle_product_ids:
                standard_price += (bundle_product.sh_cost_price *
                                   bundle_product.sh_qty)
        self.standard_price = standard_price


class ShBundleProduct(models.Model):
    _name = 'sh.product.bundle'
    _description = 'Bundle Products'

    # def _product_id_domain(self):
    # # employee_ids is considered a safe field and as such will be fetched as sudo.
    # # So try to enforce the security rules on the field to make sure we do not load employees outside of active companies
    #     print('\n\n SELF',self)
    #     return [('id', '!=', self.sh_bundle_id.product_variant_id.id)]

    sh_bundle_id = fields.Many2one('product.template', 'Bundle ID')
    sh_product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    sh_qty = fields.Float("Quantity")
    sh_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    sh_price_unit = fields.Float('Unit Price')
    sh_cost_price = fields.Float(related="sh_product_id.standard_price")
    sh_price_subtotal = fields.Float('Sub Total', readonly=True, store=True)

    @api.onchange('sh_product_id')
    def _onchange_sh_product_id(self):
        if self.sh_product_id:
            self.sh_uom = self.sh_product_id.uom_id.id
            self.sh_qty = 1.0
            self.sh_price_unit = self.sh_product_id.list_price

    @api.onchange('sh_qty', 'sh_price_unit')
    def get_price_subtotal(self):
        for rec in self:
            rec.sh_price_subtotal = rec.sh_price_unit * rec.sh_qty
