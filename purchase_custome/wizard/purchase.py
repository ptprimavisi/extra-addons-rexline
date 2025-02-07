from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseWizard(models.TransientModel):
    _name = 'purchase.order.wizard'

    mrf_id = fields.Many2one('mrf.mrf')
    partner_id = fields.Many2one('res.partner')
    picking_type_id = fields.Many2one('stock.picking.type', domain="[('code','=','incoming')]")
    order_line = fields.One2many('order.line.wizard', 'order_id')

    def action_confirm(self):
        for line in self:
            if not line.order_line:
                raise UserError('Pl add product first')
            list_line = []
            for lines in line.order_line:
                if not lines.unit_price or lines.unit_price == 0:
                    raise UserError('Unit price cannot be empty')
                list_line.append((0,0, {
                    'product_id': lines.product_id.id,
                    'name' : lines.product_id.product_tmpl_id.name,
                    'product_qty': lines.product_qty,
                    'product_uom': lines.product_uom.id,
                    'price_unit': lines.unit_price,
                    'budget': lines.budget
                }))
            doc = ''
            so = self.env['sale.order'].search([('opportunity_id', '=', line.mrf_id.inquiry_id.opportunity_id.id), ('state','=','sale')])
            if so:
                if len(so) > 1:
                    raise UserError('SO WON dokumen tidak boleh lebih dari 1 ')
                doc = str(so.name)
            po = self.env['purchase.order'].create({
                'mrf_id': line.mrf_id.id,
                'partner_id': line.partner_id.id,
                'source_doc': doc,
                'paymen_term_id' : line.partner_id.property_supplier_payment_term_id.id or False,
                'picking_type_id': line.picking_type_id.id,
                'order_line': list_line
            })
            po.button_confirm()
            line.mrf_id.message_post(body=f"Purchase order create {str(po.name)}")



class OrderLineWizard(models.TransientModel):
    _name = 'order.line.wizard'

    product_id = fields.Many2one('product.product')
    name = fields.Char()
    product_qty = fields.Float()
    unit_price = fields.Float()
    budget = fields.Float()
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]"
        # compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
        # ondelete="restrict",
    )
    order_id = fields.Many2one('purchase.order.wizard')
