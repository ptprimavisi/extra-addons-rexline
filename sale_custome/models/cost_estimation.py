from odoo import api, fields, models
from odoo.exceptions import UserError


class CostEstimation(models.Model):
    _name = "cost.estimation"

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    rfq_id = fields.Many2one('rfq.rfq')
    operation_type = fields.Selection([
        ('project', 'Project'),
        ('wo', 'Work Order')
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('final', 'Final')
    ], default="draft")
    cost_estimation_line_ids = fields.One2many('cost.estimation.line', 'cost_id')
    price_total = fields.Float()


    def action_confirm(self):
        raise UserError('test button finish')


class CostEstimationLine(models.Model):
    _name = "cost.estimation.line"

    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Float()
    product_uom = fields.Many2one('uom.uom')
    price_unit = fields.Float()
    edit_price = fields.Boolean()
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency', store=True, readonly=False, precompute=True,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals', store=True,
    )
    cost_id = fields.Many2one('cost.estimation')

    # def _compute_edit_price(self):
    #     for line in self:
    #         line.edit_price = False
    #         user_id = self.env.uid
    #
    #         # Retrieve the user record
    #         user = self.env['res.users'].browse(user_id)
    #         if user:
    #             if user.is_purchase:
    #                 line.edit_price = True

    @api.depends('quantity', 'price_unit', 'currency_id')
    def _compute_totals(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.quantity
