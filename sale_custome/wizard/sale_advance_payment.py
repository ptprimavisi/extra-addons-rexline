from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        # for line in self:
        #     if line.advance_payment_method == 'percentage':
        #         raise UserError(self.sale_order_ids)
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        if self.advance_payment_method == 'percentage':
            inv_id = res['res_id']
            print(inv_id)
            # exit()
            order_id = self.sale_order_ids
            order_line = self.env['sale.order.line'].search([('order_id','=',int(order_id)),('product_uom_qty','>',0)])
            list_order = []
            for lines in order_line:
                pembagi = self.amount / 100
                list_order.append((0,0,{
                    'product_id': lines.product_id.id,
                    'name': str(lines.product_id.product_tmpl_id.name) + '(Down Payment ' + str(self.amount) + ' %)',
                    'quantity': lines.product_uom_qty,
                    'uom_id': lines.product_uom.id,
                    'price_unit': lines.price_unit * pembagi,
                    'tax_ids': lines.tax_id
                }))
            invoice = self.env['account.move'].search([('id','=',inv_id)])
            invoice.write({
                'is_dp': True,
                'detail_ids': list_order})
        if self.advance_payment_method == 'fixed':
            inv_id = res['res_id']
            print(inv_id)
            # exit()
            order_id = self.sale_order_ids
            order_line = self.env['sale.order.line'].search([('order_id','=',int(order_id)),('product_uom_qty','>',0)])
            list_order = []
            for lines in order_line:
                pembagi = self.amount / 100
                list_order.append((0,0,{
                    'product_id': lines.product_id.id,
                    'name': str(lines.product_id.product_tmpl_id.name) + '(Down Payment ' + str(self.amount) + ' %)',
                    'quantity': lines.product_uom_qty,
                    'uom_id': lines.product_uom.id,
                    'tax_ids': lines.tax_id
                }))
            invoice = self.env['account.move'].search([('id','=',inv_id)])
            invoice.write({
                'is_dp': True,
                'detail_ids': list_order})
        if self.advance_payment_method == 'delivered' and self.amount_to_invoice != 0 or self.amount_invoiced != 0:
            inv_id = res['res_id']
            print(inv_id)
            # exit()
            order_id = self.sale_order_ids
            order_line = self.env['sale.order.line'].search([('order_id','=',int(order_id)),('product_uom_qty','>',0)])
            list_order = []
            for lines in order_line:
                pembagi = self.amount / 100
                list_order.append((0,0,{
                    'product_id': lines.product_id.id,
                    'name': str(lines.product_id.product_tmpl_id.name) + '(Down Payment ' + str(self.amount) + ' %)',
                    'quantity': lines.product_uom_qty,
                    'uom_id': lines.product_uom.id,
                    'tax_ids': lines.tax_id
                }))
            invoice = self.env['account.move'].search([('id','=',inv_id)])
            invoice.write({
                'is_dp': True,
                'detail_ids': list_order})
        # print(res['id'])
        # exit()
        return res
