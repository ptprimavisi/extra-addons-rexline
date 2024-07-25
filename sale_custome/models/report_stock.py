from odoo import models, api, fields
from odoo.exceptions import UserError


class ReportStockProject(models.Model):
    _name = 'stock.report.project'

    name = fields.Char()
    product_id = fields.Many2one('product.product')
    inquiry_id = fields.Many2one('inquiry.inquiry')
    location_id = fields.Many2one('stock.location')
    date_from = fields.Date()
    date_to = fields.Date()
    # select = fields.Selection([
    #     ('in', 'Inbound'),
    #     ('out', 'Outbound')
    # ])
    stock_awal = fields.Float()
    stock_in = fields.Float()
    stock_out = fields.Float()
    finel_stock = fields.Float()


class ReportStockProjectWizard(models.Model):
    _name = 'stock.project.wizard'

    product_id = fields.Many2one('product.product')
    inquiry_id = fields.Many2one('inquiry.inquiry')
    location_id = fields.Many2one('stock.location')
    date_from = fields.Date()
    date_to = fields.Date()


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

            product_ids = self.env['product.product'].search([('detailed_type', '=', 'product')], order="id asc").ids
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
                operation_receipt = self.env['stock.picking.type'].search([('name', '=', 'Receipts')])
                operation_do = self.env['stock.picking.type'].search(
                    [('name', '=', 'Delivery Orders')])
                do_operation_ids = tuple(operation_do.ids)
                operation_mo = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', line.location_id.id), ('name', '=', 'Manufacturing')])
                self._cr.execute("""
                WITH stock_masuk_sebelum AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS masuk_sebelum
                    FROM 
                        stock_move a
                    WHERE
                        
                        a.state = 'done' AND
                        a.write_date::date < '""" + str(line.date_from) + """' AND
                        a.location_dest_id = """ + str(line.location_id.id) + """ AND
                        a.date::date < '""" + str(line.date_from) + """' AND 
                        a.product_id = """ + str(products) + """ AND
                        a.state = 'done'
                ),
                
                stock_keluar_sebelum AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS keluar_sebelum
                    FROM 
                        stock_move a
                    WHERE
                            a.state = 'done' AND
                            a.write_date::date < '""" + str(line.date_from) + """' AND
                            a.location_id = """ + str(line.location_id.id) + """ AND
                            a.date::date < '""" + str(line.date_from) + """' AND 
                            a.product_id = """ + str(products) + """ AND
                            a.state = 'done'
                ),
                stock_penjualan_sesudah AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS penjualan_sesudah
                    FROM 
                        stock_move a
                    WHERE
                            a.state = 'done' AND
                            a.picking_type_id in """ + str(do_operation_ids) + """ AND
                            a.write_date::date >= '""" + str(line.date_from) + """' AND
                            a.write_date::date <= '""" + str(line.date_to) + """' AND
                            a.location_id = """ + str(line.location_id.id) + """ AND
                            a.date::date >= '""" + str(line.date_from) + """' AND 
                            a.date::date <= '""" + str(line.date_to) + """' AND
                            a.product_id = """ + str(products) + """ AND
                            a.state = 'done'
                ),
                
                
                stock_pembelian_sesudah AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS pembelian_sesudah
                    FROM 
                        stock_move a
                    WHERE
                            a.state = 'done' AND
                            a.picking_type_id in """ + str(tuple(operation_receipt.ids)) + """ AND
                            a.write_date::date >= '""" + str(line.date_from) + """' AND
                            a.write_date::date <= '""" + str(line.date_to) + """' AND
                            a.location_dest_id = """ + str(line.location_id.id) + """ AND
                            a.date::date >= '""" + str(line.date_from) + """' AND 
                            a.date::date <= '""" + str(line.date_to) + """' AND
                            a.product_id = """ + str(products) + """ AND
                            a.state = 'done'
                ),
                stock_masuk_sesudah AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS masuk_sesudah
                    FROM 
                        stock_move a
                    WHERE
                        
                        a.state = 'done' AND
                        a.write_date::date >= '""" + str(line.date_from) + """' AND
                        a.write_date::date <= '""" + str(line.date_to) + """' AND
                        a.location_dest_id = """ + str(line.location_id.id) + """ AND
                        a.date::date >= '""" + str(line.date_from) + """' AND 
                        a.date::date <= '""" + str(line.date_to) + """' AND
                        a.product_id = """ + str(products) + """ AND
                        a.state = 'done'
                ),
                
                stock_keluar_sesudah AS (
                    SELECT
                        COALESCE(SUM(a.quantity), 0) AS keluar_sesudah
                    FROM 
                        stock_move a
                    WHERE
                            a.state = 'done' AND
                            a.write_date::date >= '""" + str(line.date_from) + """' AND
                            a.write_date::date <= '""" + str(line.date_to) + """' AND
                            a.location_id = """ + str(line.location_id.id) + """ AND
                            a.date::date >= '""" + str(line.date_from) + """' AND 
                            a.date::date <= '""" + str(line.date_to) + """' AND 
                            a.product_id = """ + str(products) + """ AND
                            a.state = 'done'
                )
                
                
                SELECT 
                    COALESCE((SELECT masuk_sebelum FROM stock_masuk_sebelum), 0) - COALESCE((SELECT keluar_sebelum FROM stock_keluar_sebelum), 0)  AS stok_awal_sebelum,
                    COALESCE((SELECT masuk_sesudah FROM stock_masuk_sesudah), 0) AS masuk_sesudah,
                    COALESCE((SELECT keluar_sesudah FROM stock_keluar_sesudah), 0) AS keluar_sesudah,
                    
                    COALESCE((SELECT masuk_sebelum FROM stock_masuk_sebelum), 0) - COALESCE((SELECT keluar_sebelum FROM stock_keluar_sebelum), 0) +
                    COALESCE((SELECT masuk_sesudah FROM stock_masuk_sesudah), 0) - COALESCE((SELECT keluar_sesudah FROM stock_keluar_sesudah), 0)  AS stok_akhir
                FROM 
                    stock_move a
                JOIN 
                    stock_picking b ON a.picking_id = b.id
                WHERE
                    b.state = 'done';

                                """)
                for initial in self._cr.dictfetchall():
                    stock_awal = initial['stok_awal_sebelum']
                    stock_in = initial['masuk_sesudah']
                    stock_out = initial['keluar_sesudah']
                    # mutasi_in = initial['total_mutasi_in']
                    # mutasi_out = initial['total_mutasi_out']
                    # difference_stock = initial['total_selisih']
                    final_stock = initial['stok_akhir']

                mutasi.write({
                    'location_id': line.location_id.id,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'stock_awal': stock_awal,
                    'stock_in': stock_in,
                    'stock_out': stock_out,
                    'final_stock': final_stock,
                })
