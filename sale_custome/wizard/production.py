from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ManufacturWizard(models.TransientModel):
    _name = 'manufactur.wizard'

    product_id = fields.Many2one('product.product')
    schedule_date = fields.Datetime()
    product_qty = fields.Float()
    origin = fields.Char()

    def default_get(self, fields_list):
        defaults = super(ManufacturWizard, self).default_get(fields_list)

        product_id = self.env.context.get('product_id', False)
        Schedule_date = self.env.context.get('schedule_date', False)
        product_qty = self.env.context.get('product_qty', False)
        origin = self.env.context.get('origin', False)
        if product_id:
            defaults['product_id'] = product_id
            defaults['schedule_date'] = Schedule_date
            defaults['product_qty'] = product_qty
            defaults['origin'] = origin

        return defaults

    def action_save(self):
        for line in self:
            mo = self.env['mrp.production'].search([])
            create_mo = mo.create({
                'product_id': int(line.product_id.id),
                'product_qty': line.product_qty,
                'origin': str(line.origin),
                'state': 'draft'
            })
            if create_mo:
                create_mo.action_confirm()
