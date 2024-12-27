from odoo import api, fields, models
from odoo.exceptions import UserError


class InheritPurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'

    is_generate_asset=fields.Boolean()


class InheritPurchaseOrder(models.Model):
    _inherit='purchase.order'

    is_generate_asset=fields.Boolean(compute='compute_generate')

    @api.depends('order_line.qty_received')
    def compute_generate(self):
        for rec in self:
            rec.is_generate_asset = all(line.qty_received > 0 for line in rec.order_line)

    def action_generate(self):
        for rec in self:
            for product in rec.order_line:
                if all(product.is_generate_asset for line in rec.order_line):
                    raise UserError('All products have already been added to the Asset Management master.')
                if product.is_generate_asset==False:
                    vals={
                        'product_name':product.product_id.product_tmpl_id.name,
                        'qty':product.qty_received,
                        'uom_id':product.product_uom.id,
                        'value':product.qty_received*product.price_unit,
                        'purchase_id':product.order_id.id
                    }
                    manajemen_assets=self.env['manajemen.assets'].create(vals)
                    product.write({'is_generate_asset':True})
            assets=self.env['manajemen.assets'].search([('purchase_id','=',rec.id)])
            if assets:
                action = {
                    'name': 'Manajemen Assets',
                    'type': 'ir.actions.act_window',
                    'res_model': 'manajemen.assets',
                    'view_mode': 'tree,form',
                    'domain': [('purchase_id', '=', rec.id)],
                    'target': 'current',
                }
                return action
            



class ManajemenAssets(models.Model):
    _name ='manajemen.assets'

    name = fields.Char(string='Inventory Number')
    product_name=fields.Char(string='Product')
    qty=fields.Float('Quantity')
    uom_id=fields.Many2one('uom.uom')
    value=fields.Float()
    purchase_id=fields.Many2one('purchase.order')
    mac_address=fields.Char()
    serial_number=fields.Char()
    brand=fields.Char()
    tipe=fields.Char()
    prepetual=fields.Date()
    purchase_date=fields.Date()
    spesification=fields.Char()
    pic=fields.Many2one('hr.employee',string='PIC')
    location=fields.Char()
    designation=fields.Char()
    department=fields.Many2one('hr.department')
    head_department= fields.Many2one('hr.employee')
    delivered_date=fields.Date()
    returned_date=fields.Date()
    remarks=fields.Text('Remarks')
    validity_days=fields.Integer(string='Validity in Days')
    current_date=fields.Date()
    usage_number=fields.Integer(string='Number of Days in Usage')
    depreciation=fields.Float(string='Depreciation')
    current_value=fields.Float(string='Current Value')
    



