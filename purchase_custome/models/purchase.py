from odoo import models, api, fields
from odoo.exceptions import UserError


class AcoountMove(models.Model):
    _inherit = 'account.move'

    count_dp = fields.Float(compute="_compute_dp")

    def action_view_dp(self):
        for line in self:
            ids = []
            purchase_ids = line.mapped('line_ids.purchase_line_id.order_id')

            purchase_ids = list(set(purchase_ids))
            # Mengambil record purchase.order berdasarkan purchase_ids
            purchase = self.env['purchase.order'].browse(purchase_ids)

            payment_dp = self.env['payment.request.dp'].search(
                [('order_id', '=', int(purchase.id)), ('payment_state', '=', True)])
            # raise UserError(payment_dp)
            if payment_dp:
                for pay in payment_dp:
                    ids.append(pay.id)
            result = {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "domain": [('request_payment_id', 'in', ids)],
                "context": {"create": False},
                "name": "PO",
                'view_mode': 'tree,form',
            }
            return result

    def _compute_dp(self):
        for line in self:
            dp = 0
            purchase_ids = line.mapped('line_ids.purchase_line_id.order_id')
            # raise UserError(purchase_ids)

            # Memastikan purchase_ids adalah daftar unik

            purchase_ids = list(set(purchase_ids))
            # Mengambil record purchase.order berdasarkan purchase_ids
            purchase = self.env['purchase.order'].browse(purchase_ids)

            payment_dp = self.env['payment.request.dp'].search(
                [('order_id', '=', int(purchase.id)), ('payment_state', '=', True)])
            # raise UserError(payment_dp)
            if payment_dp:
                for pay in payment_dp:
                    account_payment = self.env['account.payment'].search(
                        [('request_payment_id', '=', int(pay.id)), ('state', '=', 'posted')])
                    if account_payment:
                        for pays in account_payment:
                            dp += float(pays.amount)
            line.count_dp = dp


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    budget = fields.Float()
    best_price = fields.Float(compute="_compute_best_price")
    source_po = fields.Many2one('purchase.order', compute="_compute_source_po")

    def _compute_source_po(self):
        for line in self:
            line.source_po = False
            order_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', line.product_id.id), ('order_id.state', '=', 'purchase'),
                 ('qty_received', '!=', 0)])
            if order_lines:
                min_price_line = min(order_lines, key=lambda x: x.price_unit)

                line.source_po = min_price_line.order_id.id

    def _compute_best_price(self):
        for line in self:
            line.best_price = 0
            order_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', line.product_id.id), ('order_id.state', '=', 'purchase'),
                 ('qty_received', '!=', 0)])
            if order_lines:
                min_price_unit = min(order_lines.mapped('price_unit'))
                line.best_price = min_price_unit


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    mrf_id = fields.Many2one('mrf.mrf')
    down_payment = fields.Float()
    dp_status = fields.Boolean()
    tp_value = fields.Integer(compute="_compute_tp_value")
    paymen_term_id = fields.Many2one('account.payment.term')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for line in self:
            line.paymen_term_id = False
            if line.partner_id:
                if line.partner_id.property_supplier_payment_term_id:
                    line.paymen_term_id = line.partner_id.property_supplier_payment_term_id.id

    @api.depends('partner_id')
    def _compute_tp_value(self):
        for line in self:
            line.tp_value = False
            if line.partner_id.property_supplier_payment_term_id:
                line.tp_value = line.partner_id.property_supplier_payment_term_id.id

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        mrf = self.env['mrf.mrf'].search([('id', '=', int(moves['mrf_id']))])
        if mrf:
            mrf.write({
                'quotation_state': 'yes'
            })
        return moves

    def default_get(self, vals):
        defaults = super(PurchaseOrder, self).default_get(vals)

        # Pastikan Anda memiliki konteks yang menyediakan partner_id
        mrf_id = self.env.context.get('mrf_id', False)
        order_line = self.env.context.get('order_line', False)
        # raise UserError(partner_id)
        if mrf_id and order_line:
            defaults['mrf_id'] = mrf_id
            defaults['order_line'] = order_line
        return defaults


class MaterialRequestForm(models.Model):
    _name = 'mrf.mrf'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    description = fields.Text()
    partner_id = fields.Many2one('res.partner')
    request_date = fields.Date()
    inquiry_id = fields.Many2one('inquiry.inquiry')
    sale_id = fields.Many2one('sale.order')
    due_date = fields.Date()
    quotation_state = fields.Selection([
        ('no', 'To Quotation'),
        ('yes', 'Quotation')
    ], default='no')
    count_quotation = fields.Integer(compute="_compute_count_quotation")
    mrf_line_ids = fields.One2many('mrf.line', 'mrf_id')
    validity = fields.Datetime()
    lead_time = fields.Datetime()
    is_accounting = fields.Boolean(compute="_compute_acc_user")
    to_inventory = fields.Boolean(compute='_compute_to_inventory', default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_inventory', 'To Inventory'),
        ('request', 'Request Budget'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
    ], default="draft")
    total_cost = fields.Float(compute="_compute_total_cost")
    total_budget = fields.Float(compute="_compute_total_budget")

    def unlink(self):
        for line in self:
            mrf_line = self.env['mrf.line'].search([('mrf_id', '=', int(line.id))])
            if mrf_line:
                mrf_line.unlink()
            po = self.env['purchase.order'].search([('mrf_id','=', int(line.id))])
            if po:
                po.unlink()

        return super().unlink()

    @api.depends('state')
    def _compute_to_inventory(self):
        for line in self:
            line.to_inventory = False
            if line.state == 'to_inventory':
                line.to_inventory = True

    @api.depends('mrf_line_ids.subtotal')
    def _compute_total_cost(self):
        for line in self:
            cost = 0
            for lines in line.mrf_line_ids:
                cost += lines.subtotal
            line.total_cost = cost

    @api.depends('mrf_line_ids.budget')
    def _compute_total_budget(self):
        for line in self:
            cost = 0
            for lines in line.mrf_line_ids:
                cost += lines.budget
            line.total_budget = cost

    def _compute_acc_user(self):
        for line in self:
            user = self.env.uid
            users = self.env['res.users'].browse(user)
            line.is_accounting = False
            if users.is_accounting:
                line.is_accounting = True

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        # for line in self:
        # raise UserError(moves.id)
        moves['name'] = self.env['ir.sequence'].next_by_code('MRF')
        # inquiry = self.env['inquiry.inquiry'].search([('id', '=', int(moves['inquiry_id']))])
        # if inquiry:
        #     inquiry.write({
        #         "name": self.env['ir.sequence'].next_by_code('BOQ')
        #     })
        return moves

    def action_confirm(self):
        for line in self:
            for lines in line.mrf_line_ids:
                if lines.budget == 0:
                    raise UserError('Budget cannot be empty!')
            line.state = 'confirm'

    def action_inventory(self):
        for line in self:
            #     for lines in line.mrf_line_ids:
            #         if lines.budget == 0:
            #             raise UserError('Budget cannot be empty!')
            line.state = 'to_inventory'

    def request_budget(self):
        for line in self:
            mrf = self.env['mrf.mrf'].browse(int(line.id))
            mrf.write({'state': 'request'})

    def action_cancel(self):
        for line in self:
            mrf = self.env['mrf.mrf'].browse(int(line.id))
            mrf.write({'state': 'cancel'})

    def action_count_quotation(self):
        for line in self:
            quotation = self.env['purchase.order'].search([('mrf_id', '=', int(line.id)), ('state', '!=', 'cancel')])
            list = len(quotation)
            if list == 1:
                # inquiry_record = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))],
                #                                                     limit=1)
                quotations = self.env['purchase.order'].search(
                    [('mrf_id', '=', int(line.id)), ('state', '!=', 'cancel')], limit=1)
                result = {
                    "type": "ir.actions.act_window",
                    "res_model": "purchase.order",
                    "domain": [('mrf_id', '=', int(line.id))],
                    "context": {"create": False},
                    "name": "PO",
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': int(quotations.id)
                }

            elif list > 1:
                result = {
                    "type": "ir.actions.act_window",
                    "res_model": "purchase.order",
                    "domain": [('mrf_id', '=', int(line.id))],
                    "context": {"create": False},
                    "name": "PO",
                    'view_mode': 'tree,form',
                }
            return result

    def _compute_count_quotation(self):
        for line in self:
            line.count_quotation = 0
            quotation = self.env['purchase.order'].search([('mrf_id', '=', int(line.id)), ('state', '!=', 'cancel')])
            if quotation:
                line.count_quotation = len(quotation)

    def action_rfq(self):
        for line in self:
            list_product = []
            for lines in line.mrf_line_ids:
                if lines:
                    if lines.product_id:
                        if lines.select:
                            if not lines.budget:
                                raise UserError('Budget amount cannot be empty !!')
                            list_product.append((0, 0, {
                                'product_id': lines.product_id.id,
                                'name': str(lines.product_id.product_tmpl_id.name),
                                'product_qty': lines.qty_purchase,
                                'budget': lines.budget,
                                'product_uom': lines.product_uom_id.id,
                                # 'price_unit': float(700.0)
                            }))
                    else:
                        raise UserError('Product cannot be empty')
                else:
                    raise UserError('Product lines cannot be empty')

            if list_product:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Create PO',
                    'res_model': 'purchase.order.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_mrf_id': int(line.id),
                        'default_order_line': list_product
                    }
                }
            else:
                raise UserError('Please select product item first')


class MrfLine(models.Model):
    _name = "mrf.line"

    sale_id = fields.Many2one('sale.order')
    product_id = fields.Many2one('product.product')
    select = fields.Boolean(default=True)
    type = fields.Char()
    description = fields.Char()
    specs_detail = fields.Char()
    unit_weight = fields.Float()
    total_weight = fields.Float(compute="_compute_weight")
    brand = fields.Char()
    quantity = fields.Float(default=1)
    avilable_qty = fields.Float(compute="_compute_available_qty")
    qty_purchase = fields.Float(compute='_compute_qty_purchase', readonly=False)
    unit_cost = fields.Float()
    subtotal = fields.Float(compute="_compute_subtotal")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]"
        # compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
        # ondelete="restrict",
    )
    budget = fields.Float()
    mrf_id = fields.Many2one('mrf.mrf')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier_rank', '!=', 0)]")
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_name = fields.Char(string='Attachment Name')
    is_accounting = fields.Boolean(compute="_compute_acc_user")
    is_inventory = fields.Boolean(compute="_compute_inv_user")
    wh_id = fields.Many2one('stock.warehouse', domain=lambda self: [
        ('company_id', '=', self.env['res.users'].browse(self.env.uid).company_id.id)])
    count_quotation = fields.Integer(compute="_compute_quotation")

    def action_count_quotation(self):
        for line in self:
            list = []
            purchase = self.env['purchase.order'].search(
                [('mrf_id', '=', line.mrf_id.id), ('state', 'in', ['draft', 'sent', 'to approve'])])
            purchase_line = self.env['purchase.order.line'].search(
                [('order_id', 'in', purchase.ids), ('product_id', '=', line.product_id.id)])
            for lines in purchase_line:
                list.append((0, 0, {
                    'vendor_id': lines.order_id.partner_id.id,
                    'price_unit': lines.price_unit,
                    'quantity': lines.product_qty,
                }))
            return {
                'type': 'ir.actions.act_window',
                'name': 'Count Quotation',
                'res_model': 'count.quotation',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'product_id': int(line.product_id.id),
                    'count_line': list
                }
            }

    def _compute_quotation(self):
        for line in self:
            purchase = self.env['purchase.order'].search(
                [('mrf_id', '=', line.mrf_id.id), ('state', 'in', ['draft', 'sent', 'to approve'])])
            purchase_line = self.env['purchase.order.line'].search(
                [('order_id', 'in', purchase.ids), ('product_id', '=', line.product_id.id)])
            c = 0
            if purchase_line:
                for liness in purchase_line:
                    c += 1
            line.count_quotation = c

    @api.onchange('product_id')
    def action_product(self):
        for line in self:
            line.unit_cost = False
            line.unit_weight = False
            if line.product_id:
                line.unit_cost = line.product_id.product_tmpl_id.standard_price
                line.unit_weight = line.product_id.product_tmpl_id.weight

    @api.depends('product_id')
    def _compute_available_qty(self):
        for line in self:
            line.avilable_qty = 0.0
            # raise UserError(line.product_id.id)
            if line.product_id:
                stock_quant = self.env['stock.quant'].with_context(inventory_mode=True).search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', 8)])
                total_quantity = sum(stock_quant.mapped('quantity'))
                # raise UserError(float(stock_quant.available_quantity))
                # line.avilable_qty = total_quantity
                if stock_quant:
                    line.avilable_qty = float(stock_quant.available_quantity)

    @api.depends('quantity', 'avilable_qty')
    def _compute_qty_purchase(self):
        for line in self:
            line.qty_purchase = 0.0
            if line.quantity or line.avilable_qty:
                total = line.quantity - line.avilable_qty
                if line.quantity < line.avilable_qty:
                    total = 0.0
                line.qty_purchase = total

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            subtotal = line.quantity * line.unit_cost
            line.subtotal = subtotal

    @api.depends('mrf_id.is_accounting')
    def _compute_acc_user(self):
        for line in self:
            line.is_accounting = line.mrf_id.is_accounting

    def _compute_inv_user(self):
        for line in self:
            users = self.env['res.users'].browse(self.env.uid)
            if users:
                line.is_inventory = users.is_inventory

    @api.depends('unit_weight', 'quantity')
    def _compute_weight(self):
        for line in self:
            total = line.quantity * line.unit_weight
            line.total_weight = total

    # def _compute_available_qty(self):
    #     for line in self:
    #         line.avilable_qty = 0
    #         if line.product_id:
    #             stock_quant = self.env['stock.quant'].search(
    #                 [('product_id', '=', line.product_id.id), ('location_id', '=', 8)])
    #             total_quantity = sum(stock_quant.mapped('quantity'))
    #             # line.avilable_qty = total_quantity
    #             if stock_quant:
    #                 line.avilable_qty = total_quantity

    # @api.depends('product_id')
    # def _compute_product_uom_id(self):
    #     for line in self:
    #         if line.product_id.id:
    #             line.product_uom_id = line.product_id.uom_id.id

    # partner_id = fields.Many2one('res.partner')
    # note = fields.Html()
    # attachment = fields.Binary(string='Attachment')
    # attachment_filename = fields.Char(string='Attachment Filename')
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('posted', 'Posted')
    # ], default='draft')


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    date = fields.Date()
    type = fields.Selection([
        ('dp', 'Down Payment'),
        ('bill', 'Bill')
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], default='draft')

    def action_confirm(self):
        for line in self:
            if line.type == 'dp':
                if not line.payment_request_dp_ids:
                    raise UserError('Please add Down Paymnet line first')
                for lines in line.payment_request_dp_ids:
                    po = self.env['purchase.order'].browse(lines.order_id.id)
                    amount_po = po.amount_total - po.down_payment
                    amount_dp = lines.amount
                    if amount_dp > amount_po:
                        raise UserError('Amount / amount yang sudah dibayarkan melebihi harga PO')
            if line.type == 'bill':
                if not line.payment_request_bill_ids:
                    raise UserError('Please add bill line first')
            self.message_post(body=f"This document has been confirm")
            line.state = 'confirmed'

    def action_validate(self):
        for line in self:
            if line.type == 'dp':
                if not line.payment_request_dp_ids:
                    raise UserError('Please add Down Paymnet line first')
                if line.payment_request_dp_ids:
                    for dp_line in line.payment_request_dp_ids:
                        if dp_line.payment_state == False:
                            raise UserError('Please Create DP First')
                        else:
                            payment = self.env['account.payment'].search([('request_payment_id', '=', int(dp_line.id))])
                            if payment.state != 'posted':
                                raise UserError(f'Please Confirm Vendor Payment for this PO. {dp_line.order_id.name}')

                            po = self.env['purchase.order'].browse(dp_line.order_id.id)
                            if po:
                                dp_po = po.down_payment + dp_line.amount
                                po.write({
                                    'down_payment': float(dp_po)
                                })
            if line.type == 'bill':
                if not line.payment_request_bill_ids:
                    raise UserError('Please add bill line first')
                if line.payment_request_bill_ids:
                    # raise UserError('test bill')
                    for bill_line in line.payment_request_bill_ids:
                        if bill_line.bill_status == False:
                            raise UserError('Please Create Payment First')
            self.message_post(body=f"This document has been Validate")
            line.state = 'validate'

    payment_request_dp_ids = fields.One2many('payment.request.dp', 'payment_id')
    payment_request_bill_ids = fields.One2many('payment.request.bill', 'payment_id')

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves['name'] = self.env['ir.sequence'].next_by_code('PR')

        return moves


class PaymentRequestDp(models.Model):
    _name = 'payment.request.dp'

    order_id = fields.Many2one('purchase.order',
                               domain="[('state','=','purchase'), ('invoice_status','in',['no','to invoice'])]")
    amount_total = fields.Float(compute='_compute_amount_totals')
    percentage = fields.Float()
    amount = fields.Float()
    payment_id = fields.Many2one('payment.request')
    payment_state = fields.Boolean(compute='_compute_payment_state')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], related="payment_id.state")

    def _compute_payment_state(self):
        for line in self:
            line.payment_state = False
            payment = self.env['account.payment'].search([('request_payment_id', '=', int(line.id))])
            if payment:
                line.payment_state = True

    @api.depends('order_id')
    def _compute_amount_totals(self):
        for line in self:
            line.amount_total = float(line.order_id.amount_total)

    def action_view_payment(self):
        for line in self:
            payment = self.env['account.payment'].search([('request_payment_id', '=', int(line.id))])
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "name": "Create Payment Vendor",
                'view_mode': 'form',
                "context": {"create": False},
                "res_id": int(payment.id)

            }

    def action_create_dp(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "name": "Create Payment Vendor",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    "create": False,
                    'default_request_payment_id': int(line.id),
                    'default_amount': line.amount,
                    'default_partner_id': line.order_id.partner_id.id,
                    'default_payment_type': 'outbound',
                    'default_partner_type': 'supplier',
                    'search_default_outbound_filter': 1,
                    'default_move_journal_types': ('bank', 'cash'),
                    'display_account_trust': True,
                }
            }

    @api.onchange('percentage')
    def onchange_persentage(self):
        for line in self:
            line.amount = False
            if line.percentage:
                if line.percentage > 100:
                    raise UserError('% !> 100')
                line.amount = line.amount_total * line.percentage / 100


class PaymentRequestBill(models.Model):
    _name = 'payment.request.bill'

    payment_id = fields.Many2one('payment.request')
    bill_id = fields.Many2one('account.move',
                              domain="[('journal_id','=', 2), ('move_type','=', 'in_invoice'), ('state','=', 'posted'), ('payment_state', '!=', 'paid')]")
    amount = fields.Float(compute='_compute_amount')
    bill_status = fields.Boolean(compute="_compute_bill_status")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], related="payment_id.state")

    @api.depends('bill_id')
    def _compute_bill_status(self):
        for line in self:
            line.bill_status = False
            if line.bill_id.payment_state == 'paid':
                line.bill_status = True

    @api.depends('bill_id')
    def _compute_amount(self):
        for line in self:
            line.amount = float(line.bill_id.amount_total)
            if line.bill_id.amount_residual:
                line.amount = line.bill_id.amount_residual

    def action_register_payment(self):
        for line in self:
            # raise UserError('tst')
            return line.bill_id.action_register_payment()


class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    request_payment_id = fields.Many2one('payment.request.dp')

#     def default_get(self, vals):
#         defaults = super(AccountPaymentInherit, self).default_get(vals)

#         # Pastikan Anda memiliki konteks yang menyediakan partner_id
#         # 'default_payment_type': 'outbound',
#         #             'default_partner_type': 'supplier',
#         #             'search_default_outbound_filter': 1,
#         #             'default_move_journal_types': ('bank', 'cash'),
#         #             'display_account_trust': True,
#         payment_type = self.env.context.get('default_payment_type', False)
#         partner_type = self.env.context.get('default_partner_type', False)
#         partner_id = self.env.context.get('partner_id', False)
#         payment_type = self.env.context.get('default_payment_type', False)
#         payment_type = self.env.context.get('default_payment_type', False)
#         # raise UserError(partner_id)
#         if inquiry_id:
#             defaults['inquiry_id'] = inquiry_id

#         return defaults
