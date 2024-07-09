from odoo import api, fields, models
from odoo.exceptions import UserError


class RfqWizard(models.Model):
    _name = 'rfq.rfq'

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        tracking=True,
    )
    rfq_line_ids = fields.One2many('rfq.line', 'rfq_id')
    inquiry_id = fields.Many2one('inquiry.inquiry', default=lambda self: self.env.context.get('active_ids', [])[0])
    due_date = fields.Date()
    state = fields.Selection([
        ('rfp', 'Request for Price'),
        ('boq', 'Cost Estimation'),
        ('mrf', 'MRF')
    ], default='rfp')
    date = fields.Date()
    count_boq = fields.Integer(compute="_compute_count_boq")
    operation_type = fields.Selection([
        ('project', 'Project'),
        ('wo', 'Work Order')
    ])
    # wo_state = fields.Boolean(defailt=False, compute="_compute_state_wo")

    def _compute_count_boq(self):
        for line in self:
            count_boq = 0
            boq = self.env['cost.estimation'].search([('rfq_id', '=', int(line.id))])
            if boq:
                for lines in boq:
                    count_boq += 1
            line.count_boq = count_boq

    # @api.depends('operation_type')
    # def _compute_state_wo(self):
    #     for line in self:
    #         line.wo_state = False
    #         if line.operation_type:
    #             if line.operation_type == 'wo':
    #                 line.wo_state = True

    def action_create_wo(self):
        for line in self:
            continue

    def action_count_boq(self):
        for line in self:
            if line.id:
                rfq = self.env['cost.estimation'].search([('rfq_id', '=', int(line.id))])
                if rfq:
                    result = {
                        "type": "ir.actions.act_window",
                        "res_model": "cost.estimation",
                        "domain": [('rfq_id', '=', int(line.id))],
                        "context": {"create": False},
                        "name": "Cost Estimation",
                        'view_mode': 'tree,form',
                    }
                    return result
                else:
                    raise UserError('Data Cost Estimation pada form ini tidak tersedia')

            else:
                raise UserError('ID rfq pada form tidak ada!')

    def _compute_inquiry(self):
        for line in self:
            active_ids = self.env.context.get('active_ids', [])
            # raise UserError(active_ids)
            # active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                return active_ids[0]
            else:
                return False
            # raise UserError(active_ids)

    def action_create_mrf(self):
        for line in self:
            state = self.env['rfq.rfq'].search([('id', '=', int(line.id))])
            state.write({
                'state': 'mrf'
            })
            # line.state = 'mrf'

    def action_create_boq(self):
        for line in self:
            for lines in line.rfq_line_ids:
                if lines.price_unit == 0:
                    raise UserError('The price unit field is mandatory')
                if not line.currency_id or not lines.currency_id:
                    raise UserError('The Currency field is mandatory')
            state = self.env['rfq.rfq'].search([('id', '=', int(line.id))])
            boq = self.env['cost.estimation'].search([])
            rfq_line = []
            for lines in line.rfq_line_ids:
                rfq_line.append((0,0, {
                    "product_id": lines.product_id.id,
                    "description": lines.description,
                    "quantity": lines.quantity,
                    "product_uom": lines.product_uom.id,
                    "price_unit": lines.price_unit,
                    "currency_id": lines.currency_id.id,
                }))
            datas = {
                "name": self.env['ir.sequence'].next_by_code('BOQ'),
                "partner_id": line.partner_id.id,
                "operation_type": line.operation_type,
                "rfq_id": line.id,
                "cost_estimation_line_ids": rfq_line
            }
            boq.create(datas)
            state.write({
                'state': 'boq'
            })

    def default_get(self, vals):
        defaults = super(RfqWizard, self).default_get(vals)

        # Pastikan Anda memiliki konteks yang menyediakan partner_id
        partner_id = self.env.context.get('partner_id', False)
        # raise UserError(partner_id)
        if partner_id:
            defaults['partner_id'] = partner_id

        return defaults

    # @api.model
    # def create(self, vals_list):
    #     moves = super().create(vals_list)
    #     # for line in self:
    #     # raise UserError(moves.id)
    #     inquiry = self.env['inquiry.inquiry'].search([('id', '=', int(moves['inquiry_id']))])
    #     if inquiry:
    #         inquiry.write({
    #             "name": self.env['ir.sequence'].next_by_code('BOQ')
    #         })
    #     return moves


class RfqLine(models.Model):
    _name = 'rfq.line'

    product_id = fields.Many2one('product.product')
    description = fields.Char()
    quantity = fields.Float()
    product_uom = fields.Many2one('uom.uom')
    price_unit = fields.Float()
    rfq_id = fields.Many2one('rfq.rfq')
    edit_price = fields.Boolean(compute="_compute_edit_price")
    unit_weight = fields.Float()
    total_weight = fields.Float(compute="_compute_weight")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals', store=True,
    )

    @api.depends('unit_weight', 'quantity')
    def _compute_weight(self):
        for line in self:
            total = line.quantity * line.unit_weight
            line.total_weight = total

    def _compute_edit_price(self):
        for line in self:
            line.edit_price = False
            user_id = self.env.uid

            # Retrieve the user record
            user = self.env['res.users'].browse(user_id)
            if user:
                if user.is_purchase:
                    line.edit_price = True



    @api.depends('rfq_id.currency_id')
    def _compute_currency_id(self):
        for line in self:
            if line.currency_id:
                line.currency_id = line.rfq_id.currency_id
            else:
                line.currency_id = False
            # if line.display_type == 'cogs':
            #     line.currency_id = line.company_currency_id
            # elif line.move_id.is_invoice(include_receipts=True):
            #     line.currency_id = line.move_id.currency_id
            # else:

    @api.depends('quantity', 'price_unit', 'currency_id')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            # subtotal = line.quantity * line_discount_price_unit
            #
            # # Compute 'price_total'.
            # if line.tax_ids:
            #     taxes_res = line.tax_ids.compute_all(
            #         line_discount_price_unit,
            #         quantity=line.quantity,
            #         currency=line.currency_id,
            #         product=line.product_id,
            #         partner=line.partner_id,
            #         is_refund=line.is_refund,
            #     )
            #     line.price_subtotal = taxes_res['total_excluded']
            #     line.price_total = taxes_res['total_included']
            # else:
            line.price_subtotal = line.price_unit * line.quantity
