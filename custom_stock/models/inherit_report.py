from odoo import models, fields, api, _
from odoo.fields import Date
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import re
import base64


class inheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    def do_custom_print(self):
        for line in self:
            if line.picking_type_id.code == 'internal':
                return self.env.ref('custom_stock.action_report_waybill').with_context(
                    paperformat=4, landscape=True).report_action(self)
            elif line.picking_type_id.code == 'outgoing':
                return self.env.ref('custom_stock.action_report_delivery').with_context(
                    paperformat=4, landscape=True).report_action(self)
            else:
                return self.do_print_picking()


class inheritPackingList(models.Model):
    _inherit = 'packing.list'

    def do_print_packing(self):
        for line in self:
            # raise UserError('clicked do_print_packing')
            return self.env.ref('custom_stock.action_report_packinglist').with_context(
                paperformat=4, landscape=True).report_action(self)
