from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime, time


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_create_packing(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "packing.list",
                "context": {"create": False},
                "name": "Packing List",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': int(line.id),
                    'default_partner_id': line.partner_id.id,
                    'default_street': line.partner_id.street,
                    'default_order_date': line.sale_id.date_order,
                    'default_delivery_date': line.scheduled_date,
                    'default_so_number': line.sale_id.name,
                    # 'default_po_number':
                }
            }


class PackingList(models.Model):
    _name = 'packing.list'

    picking_id = fields.Many2one('stock.picking')
    partner_id = fields.Many2one('res.partner')
    street = fields.Text()
    order_date = fields.Date()
    delivery_date = fields.Date()
    so_number = fields.Char()
    po_number = fields.Char()
    truck_no = fields.Char()
    picking_line = fields.One2many('picking.list.line', 'picking_id')


class PickingLine(models.Model):
    _name = 'picking.list.line'

    picking_id = fields.Many2one('picking.list')
    item = fields.Char()
    qty_out = fields.Float()
    uom_out = fields.Many2one('uom.uom')
    qty_kolli = fields.Float()
    uom_kolli = fields.Many2one('uom.uom')
    p = fields.Float()
    l = fields.Float()
    t = fields.Float()
    net_wight = fields.Float()
    gross_wight = fields.Float()
