from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date, datetime, time


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    count_packing_list = fields.Integer(compute="_compute_count_packing")
    no_kendaraan = fields.Char()
    jenis_kendaraan = fields.Char()
    contact_person = fields.Text()
    street = fields.Text()
    purchase_id = fields.Many2one('purchase.order', compute="_compute_purchase")
    show_po_number = fields.Boolean(compute='_compute_show_po_number')

    @api.depends_context('restricted_picking_type_code')
    def _compute_show_po_number(self):
        for rec in self:
            rec.show_po_number = False
            po = self.env.context.get('restricted_picking_type_code')
            if po == 'incoming':
                rec.show_po_number = True

            # raise UserError(rec.show_po_number)

    @api.depends('move_ids_without_package')
    def _compute_purchase(self):
        for line in self:
            line.purchase_id = False
            if line.move_ids_without_package:
                purchase_lines = line.move_ids_without_package.mapped('purchase_line_id')
                order_lines = self.env['purchase.order.line'].search([
                    ('id', 'in', purchase_lines.ids)
                ])
                if order_lines:
                    purchase_id = order_lines.mapped('order_id')
                    line.purchase_id = int(purchase_id)

    @api.onchange('partner_id')
    def oc_partenr(self):
        for line in self:
            line.street = False
            if line.partner_id:
                street = '' if line.partner_id.street is False else line.partner_id.street
                city = f'{line.partner_id.city},' if line.partner_id.city is not False else ''
                state = f'{line.partner_id.state_id.name},' if line.partner_id.state_id.name is not False else ''
                country = f'{line.partner_id.country_id.name}' if line.partner_id.country_id.name is not False else ''
                string = f'{street} {city} {state} {country}'
                line.street = string

    def _compute_count_packing(self):
        for line in self:
            picking = self.env['packing.list'].search([('picking_id','=',int(line.id))])
            line.count_packing_list = len(picking)

    def action_view_packing(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "packing.list",
                "domain": [('picking_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "Packing List",
                'view_mode': 'tree,form',
            }

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

    picking_id = fields.Many2one('packing.list')
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
