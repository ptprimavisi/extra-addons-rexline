from odoo import models, api, fields
from datetime import datetime
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_sync_so(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sync Sale Order',
            'res_model': 'sinkron.wizard.so',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }





