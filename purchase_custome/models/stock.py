from odoo import fields, models, api
from odoo.exceptions import UserError


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    location_rak = fields.Many2many('location.tag')


class LocationTag(models.Model):
    _name = 'location.tag'
    _description = 'Location Tags'

    name = fields.Char()


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    borrowing_ids = fields.One2many('asset.borrowing', 'product_tmpl_id')


class AssetBorrowing(models.Model):
    _name = 'asset.borrowing'
    _description = 'Asset Borrowing'

    borrow_date = fields.Date()
    pic = fields.Many2one('hr.employee')
    pic_description = fields.Char()
    product_tmpl_id = fields.Many2one('product.template')
    quantity = fields.Float()
    product_uom_category_id = fields.Many2one(related='product_tmpl_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', domain="[('category_id', '=', product_uom_category_id)]")
    so = fields.Char()
    project = fields.Char()
    estimate_return_date = fields.Date()
    deadline = fields.Float()
    remark = fields.Float()
    status = fields.Float()

    @api.onchange('product_tmpl_id')
    def onchange_product(self):
        for line in self:
            line.uom_id = False
            if line.product_tmpl_id:
                line.uom_id = line.product_tmpl_id.uom_id.id
