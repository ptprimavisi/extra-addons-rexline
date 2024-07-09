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
                self._cr.execute("""
                                    WITH stok_sebelum_tanggal AS (
                    SELECT
                        COALESCE(quantity, 0) AS total_stok_awal
                    FROM 
                        stock_move_line
                    WHERE 
                        product_id = '""" + str(products) + """' AND 
                        date::date >= '2024-03-03' AND
                        location_dest_id = '8' AND
                        picking_id IS NULL AND 
                        state = 'done'
                    ORDER BY date::date DESC
                    LIMIT 1
                ),
                masuk_sebelum_tanggal AS (
                			SELECT
                					COALESCE(SUM (CASE 
                											WHEN b.picking_type_id IN (6, 9) AND b.partner_id NOT IN (72014, 79880, 72014, 79891, 81471)  THEN a.quantity 
                											ELSE 0 
                									END), 0) AS stok_masuk_terakhir
                			FROM 
                					stock_move_line a
                					JOIN 
                							stock_picking b ON a.picking_id = b.id
                			WHERE 
                							b.date::date > '2024-03-04' AND 
                							b.date::date < '""" + str(line.date_from) + """' AND 
                							a.product_id = '""" + str(products) + """' AND
                                            (b.state = 'done')
                ),
                mutasi_in_sebelum_tanggal AS (
                    SELECT
                        COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (6, 9) AND b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0) AS mutasi_in_terakhir
                    FROM 
                        stock_move_line a
                        JOIN 
                            stock_picking b ON a.picking_id = b.id
                    WHERE 
                            b.date > '2024-03-04' AND 
                            b.date::date < '""" + str(line.date_from) + """' AND 
                            a.product_id = '""" + str(products) + """' AND
                            (b.state = 'done')
                ),
                 keluar_sebelum_tanggal AS (
                     SELECT
                         COALESCE(SUM(CASE 
                                     WHEN b.picking_type_id IN (2, 10) AND b.partner_id != 72014  THEN a.quantity 
                                     ELSE 0 
                                 END), 0) AS stok_keluar_terakhir
                     FROM 
                         stock_move_line a
                         JOIN 
                             stock_picking b ON a.picking_id = b.id
                     WHERE 
                             CASE
                             WHEN b.date_done IS NOT NULL AND b.date_done > b.date THEN b.date_done
                             ELSE b.date
                 						END::date > '2024-03-04' AND 
                 						CASE
                 								WHEN b.date_done IS NOT NULL AND b.date_done > b.date THEN b.date_done
                 								ELSE b.date
                 						END::date <= '""" + str(line.date_to) + """' AND 
                             a.product_id = '""" + str(products) + """' AND
                 			(b.state = 'done')
                 ),
                mutasi_out_sebelum_tanggal AS (
                    SELECT
                        COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (2, 10) AND b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0) AS mutasi_out_terakhir
                    FROM 
                        stock_move_line a
                        JOIN 
                            stock_picking b ON a.picking_id = b.id
                    WHERE 
                            b.date > '2024-03-04' AND 
                            b.date::date < '""" + str(line.date_from) + """' AND 
                            a.product_id = '""" + str(products) + """' AND
                            (b.state = 'done')
                ),
                
                adjustment_in AS (
                			SELECT
                					COALESCE(SUM (CASE 
                											WHEN b.picking_type_id IN (11) THEN a.quantity 
                											ELSE 0 
                									END), 0) AS adjust_in
                			FROM 
                					stock_move_line a
                					JOIN 
                							stock_picking b ON a.picking_id = b.id
                			WHERE 
                							b.date::date > '2024-03-04' AND 
                							b.picking_type_id = 11 AND
                							a.product_id = '""" + str(products) + """' AND
                                            (b.state = 'done')
                ),
                adjustment_out AS (
                			SELECT
                					COALESCE(SUM (CASE 
                											WHEN b.picking_type_id IN (12) THEN a.quantity 
                											ELSE 0 
                									END), 0) AS adjust_out
                			FROM 
                					stock_move_line a
                					JOIN 
                							stock_picking b ON a.picking_id = b.id
                			WHERE 
                							b.date::date > '2024-03-04' AND 
                							b.picking_type_id = 12 AND
                							a.product_id = '""" + str(products) + """' AND
                                            (b.state = 'done')
                )

                SELECT 
                    COALESCE((SELECT total_stok_awal FROM stok_sebelum_tanggal), 0) AS stok_awal_terakhir,

                	COALESCE((SELECT stok_masuk_terakhir FROM masuk_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (6, 9) AND  b.partner_id NOT IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0) AS total_stok_masuk,

                	

                	COALESCE((SELECT mutasi_in_terakhir FROM mutasi_in_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (6, 9) AND b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0) AS total_mutasi_in,								

                	COALESCE((SELECT mutasi_out_terakhir FROM mutasi_out_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (2, 10) AND  b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0) AS total_mutasi_out,

                    COALESCE((SELECT adjust_in FROM adjustment_in), 0) - COALESCE((SELECT adjust_out FROM adjustment_out), 0) AS total_selisih,	

                	COALESCE((SELECT total_stok_awal FROM stok_sebelum_tanggal), 0) +
                        (COALESCE((SELECT stok_masuk_terakhir FROM masuk_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (6, 9) AND  b.partner_id NOT IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0)) + 
                		(COALESCE((SELECT mutasi_in_terakhir FROM mutasi_in_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (6, 9) AND  b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0)) - 
                		(COALESCE((SELECT mutasi_out_terakhir FROM mutasi_out_sebelum_tanggal), 0) + COALESCE(SUM(CASE 
                                    WHEN b.picking_type_id IN (2, 10) AND  b.partner_id IN (72014, 79880, 72014, 79891, 81471) THEN a.quantity 
                                    ELSE 0 
                                END), 0)) + 
                        (COALESCE((SELECT adjust_in FROM adjustment_in), 0) - COALESCE((SELECT adjust_out FROM adjustment_out), 0)) AS final_stok
                FROM 
                    stock_move_line a
                JOIN 
                    stock_picking b ON a.picking_id = b.id
                WHERE
                		 CASE
                            WHEN b.date_done IS NOT NULL AND b.date_done > b.date THEN b.date_done
                            ELSE b.date
                						END::date >= '""" + str(line.date_from) + """' AND 
                						CASE
                								WHEN b.date_done IS NOT NULL AND b.date_done > b.date THEN b.date_done
                								ELSE b.date
                						END::date <= '""" + str(line.date_to) + """' AND
                    a.product_id = '""" + str(products) + """' AND
                    (b.state = 'done');

                                """)
                for initial in self._cr.dictfetchall():
                    stock_awal = initial['stok_awal_terakhir']
                    stock_in = initial['total_stok_masuk']
                    # stock_out = initial['total_stok_keluar']
                    # mutasi_in = initial['total_mutasi_in']
                    # mutasi_out = initial['total_mutasi_out']
                    # difference_stock = initial['total_selisih']
                    final_stock = initial['final_stok']

                mutasi.write({
                    'stock_awal': stock_awal,
                    'stock_in': stock_in,
                    'stock_out': stock_out,
                    'final_stock': final_stock,
                })

