from odoo import models, api, fields
from odoo.exceptions import UserError
import xlsxwriter
import xlwt


class ReportStockProject(models.Model):
    _name = 'stock.report.project'

    name = fields.Char()
    product_id = fields.Many2one('product.product')
    category = fields.Char()
    inquiry_id = fields.Many2one('inquiry.inquiry')
    location_id = fields.Many2one('stock.location')
    date_from = fields.Date()
    date_to = fields.Date()
    stock_awal = fields.Float()
    stock_in = fields.Float()
    stock_out = fields.Float()
    unbuild = fields.Float()
    # final_stock = fields.Float()

    def action_generate_period(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.project.wizard",
            # "context": {"create": False},
            "name": "Generate Report",
            'view_mode': 'form',
            'target': 'new',
        }


class ReportStockProjectWizard(models.Model):
    _name = 'stock.project.wizard'

    product_id = fields.Many2many('product.product')
    inquiry_id = fields.Many2one('inquiry.inquiry')
    location_id = fields.Many2one('stock.location', domain=[('usage', '=', 'internal')])
    date_from = fields.Date()
    date_to = fields.Date()

    def action_save(self):
        for line in self:
            self._cr.execute("DELETE FROM stock_report_project;")
            if line.inquiry_id:
                product_ids = line.inquiry_id.inquiry_line_detail.mapped('product_id.id')
                # for liness in line.inquiry_id.inquiry_line_detail:

            # product_ids = self.env['product.product'].search([('detailed_type', '=', 'product')], order="id asc").ids
            if line.product_id:
                product_ids = line.product_id.ids
            # raise UserError(product_ids)
            for products in product_ids:
                stock_awal = 0.0
                stock_in = 0.0
                stock_out = 0.0
                # final_stock = 0.0
                project_category = 'False'
                if line.inquiry_id:
                    project_category = line.inquiry_id.project_category

                product = self.env['product.product'].search([('id', '=', int(products))])
                mutasi = self.env['stock.report.project'].create({
                    'name': str(product.product_tmpl_id.name),
                    'product_id': product.id
                })
                operation_receipt = self.env['stock.picking.type'].search([('name', '=', 'Receipts')])
                operation_do = self.env['stock.picking.type'].search(
                    [('name', '=', 'Delivery Orders')])

                receipts_operation_ids = tuple(operation_receipt.ids)
                if len(receipts_operation_ids) == 1:
                    operation_receipts_ids = f"({receipts_operation_ids[0]})"
                else:
                    operation_receipts_ids = str(receipts_operation_ids)

                do_operation_ids = tuple(operation_do.ids)
                if len(do_operation_ids) == 1:
                    operation_do_ids = f"({do_operation_ids[0]})"
                else:
                    operation_do_ids = str(do_operation_ids)
                operation_mo = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', line.location_id.id), ('name', '=', 'Manufacturing')])
                self._cr.execute("""
                WITH stock_masuk_project AS (
                    SELECT
                        COALESCE(SUM(sm.quantity), 0) AS stock_masuk
                    FROM
                        stock_move sm
                    JOIN
                        stock_picking sp on sm.picking_id = sp.id 
                    JOIN
                        purchase_order_line pol  on sm.purchase_line_id  = pol.id
                    JOIN
                        purchase_order po on pol.order_id = po.id
                    JOIN
                        mrf_mrf mm on po.mrf_id = mm.id
                    WHERE
                        sm.state = 'done' AND
                        sm.write_date::date >= '""" + str(line.date_from) + """' AND
                        sm.write_date::date <= '""" + str(line.date_to) + """' AND
                        sm.location_dest_id = """ + str(line.location_id.id) + """ AND
                        sm.date::date >= '""" + str(line.date_from) + """' AND
                        sm.date::date <= '""" + str(line.date_to) + """' AND  
                        sm.product_id = """ + str(products) + """ AND
                        mm.inquiry_id = """ + str(line.inquiry_id.id) + """
                ),
                stock_consume_project AS (
                    SELECT
                        COALESCE(SUM(prl.qty_consume), 0) AS stock_consume
                    FROM
                        mrp_production mp
                    JOIN
                        inquiry_line_task ilt on mp.id = ilt.mo_id
                    JOIN
                        inquiry_inquiry ii on ilt.inquiry_id = ii.id 
                    JOIN
                        production_report pr on pr.mo_id = mp.id
                    JOIN 
                        production_report_line prl on prl.production_id = pr.id
                    WHERE
                        pr.state = 'done' AND
                        mp.location_src_id = """ + str(line.location_id.id) + """ AND
                        pr.activity_date::date >= '""" + str(line.date_from) + """' AND
                        pr.activity_date::date <= '""" + str(line.date_to) + """' AND  
                        prl.product_id = """ + str(products) + """ AND
                        ii.id = """ + str(line.inquiry_id.id) + """
                ),
                stock_yang_dibutuhakan AS (
                    SELECT COALESCE(SUM(id.product_uom_quantity), 0) AS stock_awal
                    FROM
                        inquiry_line_detail id
                    WHERE
                        id.inquiry_id = """+ str(line.inquiry_id.id) +""" AND 
                        id.product_id = """+ str(products) +"""
                ),
                stock_unbuild_project AS (
                    SELECT COALESCE(SUM(sm.quantity),0) AS stock_unbuild
                    FROM 
                        stock_move sm
                    JOIN
                        mrp_unbuild mu on sm.unbuild_id = mu.id
                    JOIN
                        mrp_production mp on mu.mo_id = mp.id
                    JOIN 
                        inquiry_line_task ilt on mp.id = ilt.mo_id
                    WHERE
                        sm.state = 'done' AND
                        sm.location_dest_id = """ + str(line.location_id.id) + """ AND
                        sm.date::date >= '""" + str(line.date_from) + """' AND
                        sm.date::date <= '""" + str(line.date_to) + """' AND  
                        sm.product_id = """ + str(products) + """ AND
                        ilt.inquiry_id = """ + str(line.inquiry_id.id) + """
                )
                SELECT 
                    COALESCE((SELECT stock_masuk FROM stock_masuk_project), 0) AS stock_masuk,
                    COALESCE((SELECT stock_consume FROM stock_consume_project), 0) AS stock_metu,
                    COALESCE((SELECT stock_awal FROM stock_yang_dibutuhakan), 0) AS stock_awal,
                    COALESCE((SELECT stock_unbuild FROM stock_unbuild_project), 0) AS unbuild_in
                FROM 
                    stock_move a
                WHERE
                    a.state = 'done';

                                """)
                for initial in self._cr.dictfetchall():
                    stock_awal = initial['stock_awal']
                    stock_in = initial['stock_masuk']
                    stock_out = initial['stock_metu']
                    unbuild = initial['unbuild_in']
                    # final_stock = initial['stok_akhir']
                # raise UserError(line.inquiry_id.id)
                inq_id = line.inquiry_id.id
                mutasi.write({
                    'category': str(project_category),
                    'inquiry_id': inq_id,
                    'location_id': line.location_id.id,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'stock_awal': stock_awal,
                    'stock_in': stock_in,
                    'stock_out': stock_out,
                    'unbuild': unbuild
                    # 'final_stock': 0
                })


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

                receipts_operation_ids = tuple(operation_receipt.ids)
                if len(receipts_operation_ids) == 1:
                    operation_receipts_ids = f"({receipts_operation_ids[0]})"
                else:
                    operation_receipts_ids = str(receipts_operation_ids)

                do_operation_ids = tuple(operation_do.ids)
                if len(do_operation_ids) == 1:
                    operation_do_ids = f"({do_operation_ids[0]})"
                else:
                    operation_do_ids = str(do_operation_ids)
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
                            a.picking_type_id in """ + str(operation_do_ids) + """ AND
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
                            a.picking_type_id in """ + str(operation_receipts_ids) + """ AND
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
