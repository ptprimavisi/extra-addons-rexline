from odoo import models, api, fields
from odoo.exceptions import UserError


class ReportStock(models.Model):
    _name = 'stock.report.period'

    name = fields.Char()
    product_id = fields.Many2one('product.product')
    location_id = fields.Many2one('stock.location')
    date_from = fields.Date()
    date_to = fields.Date()
    stock_awal = fields.Float()
    stock_in = fields.Float()
    stock_out = fields.Float()
    final_stock = fields.Float()

    def action_generate_period(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.report.wizard",
            # "context": {"create": False},
            "name": "Generate Report",
            'view_mode': 'form',
            'target': 'new',
        }


class ReportStockWizard(models.Model):
    _name = 'stock.report.wizard'

    product_id = fields.Many2many('product.product')
    location_id = fields.Many2one("stock.location", domain=[('usage', '=', 'internal')])
    date_from = fields.Date()
    date_to = fields.Date()

    def action_save(self):
        for line in self:
            self._cr.execute("DELETE FROM stock_report_period;")

            product_ids = self.env['product.product'].search([], order="id asc").ids
            if line.product_id:
                product_ids = line.product_id.ids
            # raise UserError(product_ids)
            for products in product_ids:
                stock_awal = 0.0
                stock_in = 0.0
                stock_out = 0.0
                final_stock = 0.0

                product = self.env['product.product'].search([('id', '=', int(products))])
                mutasi = self.env['stock.report.period'].create({
                    'name': str(product.product_tmpl_id.name),
                    'product_id': product.id
                })
                operation_receipt = self.env['stock.picking.type'].search([('default_location_dest_id','=', line.location_id.id), ('name','=', 'Receipts')])
                operation_do = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', line.location_id.id), ('name', '=', 'Delivery Orders')])
                self._cr.execute("""
                WITH stock_masuk_sebelum AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS masuk_sebelum
                    FROM 
                        stock_move a
                        JOIN 
                            stock_picking b ON a.picking_id = b.id
                    WHERE
                            a.state = 'done' AND
                            b.date_done::date < '""" + str(line.date_from) + """' AND
                            a.location_dest_id = """ + str(line.location_id.id) + """ AND
                            a.picking_type_id =  """ + str(operation_receipt.id) + """ AND
                            b.date::date < '""" + str(line.date_from) + """' AND 
                            a.product_id = """ + str(products) + """ AND
                            b.state = 'done'
                ),
                
                stock_penjualan_sebelum AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS penjualan_sebelum
                    FROM 
                        stock_move a
                        JOIN 
                            stock_picking b ON a.picking_id = b.id
                    WHERE
                            a.state = 'done' AND
                            b.date_done::date < '""" + str(line.date_from) + """' AND
                            a.location_id = """ + str(line.location_id.id) + """ AND
                            a.picking_type_id =  """ + str(operation_do.id) + """ AND
                            b.date::date < '""" + str(line.date_from) + """' AND 
                            a.product_id = """ + str(products) + """ AND
                            b.state = 'done'
                )

                SELECT 
                    COALESCE((SELECT masuk_sebelum FROM stock_masuk_sebelum), 0) AS stok_awal_sebelum
                FROM 
                    stock_move_line a
                JOIN 
                    stock_picking b ON a.picking_id = b.id
                WHERE
                    b.state = 'done';

                                """)
                for initial in self._cr.dictfetchall():
                    stock_awal = initial['stok_awal_sebelum']
                    # stock_in = initial['total_stok_masuk']
                    # stock_out = initial['total_stok_keluar']
                    # mutasi_in = initial['total_mutasi_in']
                    # mutasi_out = initial['total_mutasi_out']
                    # difference_stock = initial['total_selisih']
                    # final_stock = initial['final_stok']

                mutasi.write({
                    'location_id': line.location_id.id,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'stock_awal': stock_awal,
                    'stock_in': stock_in,
                    'stock_out': stock_out,
                    'final_stock': final_stock,
                })
