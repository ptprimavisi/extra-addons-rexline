from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz


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
            three_years_ago = (datetime.today() - timedelta(days=3 * 365)).strftime('%Y-%m-%d')
            order_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', line.product_id.id), ('order_id.state', '=', 'purchase'),
                 ('qty_received', '!=', 0), ('date_planned', '>=', three_years_ago)])
            if order_lines:
                min_price_line = min(order_lines, key=lambda x: x.price_unit)

                line.source_po = min_price_line.order_id.id

    def _compute_best_price(self):
        for line in self:
            line.best_price = 0
            three_years_ago = (datetime.today() - timedelta(days=3 * 365)).strftime('%Y-%m-%d')
            order_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', line.product_id.id), ('order_id.state', '=', 'purchase'),
                 ('qty_received', '!=', 0), ('date_planned', '>=', three_years_ago)])
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
    source_doc = fields.Char()
    tag_ids = fields.Many2many('purchase.tag')
    sale_id = fields.Many2one('sale.order', compute="_compute_sale_order")

    @api.depends('mrf_id')
    def _compute_sale_order(self):
        for line in self:
            line.sale_id = False
            if line.mrf_id:
                if line.mrf_id.inquiry_id.sale_id:
                    line.sale_id = line.mrf_id.inquiry_id.sale_id.id

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


class PurchaseTag(models.Model):
    _name = 'purchase.tag'

    name = fields.Char()


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
    total_budget_use = fields.Float(compute="_compute_total_budget_use")
    picking_type_id = fields.Many2one('stock.picking.type', domain="[('code','=','incoming')]")
    department_id = fields.Many2one('hr.department')

    def action_print(self):
        return self.env.ref('custom_report.action_report_mrf').with_context(
            paperformat=4, landscape=True).report_action(self)

    def unlink(self):
        for line in self:
            mrf_line = self.env['mrf.line'].search([('mrf_id', '=', int(line.id))])
            if mrf_line:
                mrf_line.unlink()
            po = self.env['purchase.order'].search([('mrf_id', '=', int(line.id))])
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
                cost += lines.subtotal_budget
            line.total_budget = cost

    @api.depends('mrf_line_ids.budget_use')
    def _compute_total_budget_use(self):
        for line in self:
            cost = 0
            for lines in line.mrf_line_ids:
                cost += lines.budget_use
            line.total_budget_use = cost

    def _compute_acc_user(self):
        for line in self:
            user = self.env.uid
            users = self.env['res.users'].browse(user)
            line.is_accounting = False
            if self.env.user.has_group('sale_custome.cost_control'):
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
            # for lines in line.mrf_line_ids:
            #     if lines.budget == 0:
            #         raise UserError('Budget cannot be empty!')
            #     if lines.qty_budget == 0:
            #         raise UserError('Please fill Qty Budget first!')
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
                        'default_picking_type_id': line.picking_type_id.id,
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
    qty_onhand = fields.Float(compute="_compute_qty_onhand")
    avilable_qty = fields.Float(compute="_compute_available_qty")
    qty_purchase = fields.Float()
    qty_ordered = fields.Float(compute='_compute_ordered')
    qty_received = fields.Float(compute='_compute_received')
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
    qty_budget = fields.Float()
    budget = fields.Float()
    subtotal_budget = fields.Float(compute="_compute_sub_budget")
    budget_use = fields.Float(compute="_budget_use", store=True)
    best_price = fields.Float(compute="_compute_bestprice", store=True)
    mrf_id = fields.Many2one('mrf.mrf')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier_rank', '!=', 0)]")
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_name = fields.Char(string='Attachment Name')
    is_accounting = fields.Boolean(compute="_compute_acc_user")
    is_inventory = fields.Boolean(compute="_compute_inv_user")
    schedule_date = fields.Date()
    wh_id = fields.Many2one('stock.warehouse', domain=lambda self: [
        ('company_id', '=', self.env['res.users'].browse(self.env.uid).company_id.id)])
    count_quotation = fields.Integer(compute="_compute_quotation")
    year = fields.Float()

    @api.depends('product_id')
    def _budget_use(self):
        for line in self:
            if line.mrf_id:
                purchase = self.env['purchase.order.line'].search(
                    [('order_id.mrf_id', '=', line.mrf_id.id), ('state', '=', 'purchase'),
                     ('product_id', '=', line.product_id.id)])
                line.budget_use = sum(purchase.mapped('price_unit'))

    @api.depends('qty_budget', 'budget')
    def _compute_sub_budget(self):
        for line in self:
            line.subtotal_budget = line.qty_budget * line.budget

    def _compute_bestprice(self):
        for line in self:
            line.best_price = 0
            order_lines = self.env['purchase.order.line'].search(
                [('product_id', '=', line.product_id.id), ('order_id.state', '=', 'purchase'),
                 ('qty_received', '!=', 0)])
            if line.year:
                # raise UserError(datetime(2024, 1, 1))
                order_lines_y = self.env['purchase.order.line'].search(
                    [('product_id', '=', line.product_id.id),
                     ('order_id.state', '=', 'purchase'),
                     ('qty_received', '!=', 0),
                     ('date_planned', '>=', datetime(int(line.year), 1, 1)),
                     ('date_planned', '<=', datetime(int(line.year), 12, 31))
                     ]
                )
                if order_lines_y:
                    order_lines = order_lines_y
            if order_lines:
                min_price_unit = min(order_lines.mapped('price_unit'))
                line.best_price = min_price_unit

    def _compute_ordered(self):
        for line in self:
            purchase = self.env['purchase.order.line'].search(
                [('order_id.mrf_id', '=', int(line.mrf_id.id)), ('state', '=', 'purchase'),
                 ('product_id', '=', line.product_id.id)])
            line.qty_ordered = sum(purchase.mapped('product_qty'))

    def _compute_received(self):
        for line in self:
            purchase = self.env['purchase.order.line'].search(
                [('order_id.mrf_id', '=', int(line.mrf_id.id)), ('order_id.state', '=', 'purchase'),
                 ('product_id', '=', line.product_id.id)])
            print(purchase)
            line.qty_received = sum(purchase.mapped('qty_received'))

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
    def _compute_qty_onhand(self):
        for line in self:
            line.qty_onhand = 0
            if line.product_id:
                stock_quant = self.env['stock.quant'].with_context(inventory_mode=True).search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', 8)])
                total_quantity = sum(stock_quant.mapped('quantity'))
                # raise UserError(float(stock_quant.available_quantity))
                # line.avilable_qty = total_quantity
                if stock_quant:
                    line.qty_onhand = float(stock_quant.quantity)

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


AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium')
]


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    priority = fields.Selection(AVAILABLE_PRIORITIES, select=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    date = fields.Date(default=lambda self: fields.Datetime.today())
    due_date = fields.Date()
    type = fields.Selection([
        ('dp', 'Down Payment'),
        ('bill', 'Full Bill')
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], default='draft')
    bank_name = fields.Char()
    bank_number = fields.Char()
    account_holder = fields.Char()
    datetime_confirm = fields.Datetime()
    department_id = fields.Many2one('hr.department')
    customer = fields.Char()
    mrf = fields.Char()
    sale_order = fields.Char()
    purchase_order = fields.Char()
    payment_category = fields.Selection([
        ('local', 'Local'),
        ('overseas', 'Overseas'),
        ('tracking', 'Trucking')
    ], default='local')

    @api.onchange('payment_request_bill_ids.bill_id')
    def onchange_order_id(self):
        print('bill id')

    def datetime_c(self, format):
        # Ambil datetime dari database (biasanya UTC)
        if format:
            datetime_utc = format  # record = instance dari model

            # Set timezone lokal
            tz = pytz.timezone('Asia/Jakarta')

            # Konversi ke lokal timezone
            datetime_local = datetime_utc.astimezone(tz)

            # Format jika diperlukan
            formatted = datetime_local.strftime('%d-%m-%Y %H:%M:%S')
        else:
            formatted = ''
        return formatted

    def approval_data(self):
        for line in self:
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            approval = self.env['multi.approval'].search(
                [('origin_ref', '=', origin_ref)],
                order='create_date desc',
                limit=1
            )
            status = ''
            date_confirm = ''
            if line.datetime_confirm:
                date_confirm = self.datetime_c(line.datetime_confirm)
            if line.state != 'draft':
                status = 'Approved'

            approval_list = [
                {
                    'name': "Requester",
                    'status': str(status),
                    'users': str(line.user_id.name),
                    'date': str(date_confirm),
                },
            ]
            if approval:
                for lines in approval.line_ids:
                    datetime_utc = lines.write_date  # record = instance dari model

                    # Set timezone lokal
                    formatted = self.datetime_c(datetime_utc)
                    approval_list.append({
                        'name': str(lines.name),
                        'status': str(lines.state),
                        'users': str(lines.user_id.name),
                        'date': str(formatted),
                    })
            return approval_list

    def action_confirm(self):
        for line in self:
            if line.type == 'dp':
                if not line.payment_request_dp_ids:
                    raise UserError('Please add Down Paymnet line first')
                if len(line.payment_request_dp_ids) > 1:
                    raise UserError('Document PO Cannot be More Than 1')
                for lines in line.payment_request_dp_ids:
                    po = self.env['purchase.order'].browse(lines.order_id.id)
                    amount_po = po.amount_total - po.down_payment
                    amount_dp = lines.amount
                    if amount_dp > amount_po:
                        raise UserError('Amount / amount yang sudah dibayarkan melebihi harga PO')
            if line.type == 'bill':
                if not line.payment_request_bill_ids:
                    raise UserError('Please add bill line first')
                if len(line.payment_request_bill_ids) > 1:
                    raise UserError('Document Bill Cannot be More Than 1')
            self.message_post(body=f"This document has been confirm")
            line.datetime_confirm = fields.Datetime.now()
            line.state = 'confirmed'

    def action_print(self):
        for line in self:
            if line.type == 'dp':
                po_ids = []
                list = []
                # bank_list = [
                #     {
                #         'bank_name': line.bank_name,
                #         'bank_number': line.bank_number,
                #         'account_holder': line.account_holder,
                #     }
                # ]
                type = 'Down Payment'
                if line.payment_request_dp_ids:
                    price_dp = 0
                    for lines in line.payment_request_dp_ids:
                        if lines.order_id:
                            # for bank_line in lines.order_id.partner_id.bank_ids:
                            #     bank_list.append({
                            #         'bank_name': bank_line.bank_id.name,
                            #         'bank_number': bank_line.acc_number,
                            #         'bank_partner': bank_line.partner_id.name
                            #     })
                            price_dp += lines.amount
                            percent = ''
                            if lines.percentage:
                                percent = f'{int(lines.percentage)}%'
                            desc = f'Down Payment {percent} of PO {lines.order_id.name}'
                            po_ids.append(lines.order_id.id)
                            po = lines.purchase_order or ''
                            vendor = lines.order_id.partner_id.name or ''
                            mrf_data = self.env['mrf.mrf'].search([('id', '=', lines.order_id.mrf_id.id)])
                            mrf = lines.mrf or ''
                            so = lines.sale_order or ''
                            cust = lines.customer or ''
                            # if mrf_data:
                            #     mrf = lines.mrf or ''
                            #     so_data = self.env['sale.order'].search(
                            #         [('opportunity_id', '=', lines.order_id.mrf_id.inquiry_id.opportunity_id.id),
                            #          ('state', '=', 'sale')], limit=1)
                            #     if so_data:
                            #         so = lines.sale_order or ''
                            #     else:
                            #         so = ''
                            # else:
                            #     so = ''
                            #     mrf = ''
                        else:
                            desc = ''
                            vendor = ''
                            mrf = ''
                            so = ''
                            po = ''
                else:
                    price_dp = 0
                    desc = ''
                    vendor = ''
                    mrf = ''
                    so = ''
                    po = ''
                purchase_data = self.env['purchase.order'].browse(po_ids)
                currency = purchase_data.currency_id.name or ''
                symbol = purchase_data.currency_id.symbol
                for po_lines in purchase_data.order_line:
                    list.append({
                        'product': po_lines.product_id.name,
                        'price_total': po_lines.price_total
                    })
            if line.type == 'bill':
                price_dp = 0
                po_ids = []
                list = []
                type = 'Full Payment'
                desc = ''
                # bank_list = [
                #     {
                #         'bank_name': line.bank_name,
                #         'bank_number': line.bank_number,
                #         'account_holder': line.account_holder,
                #     }
                # ]
                if line.payment_request_bill_ids:
                    for lines in line.payment_request_bill_ids:
                        if lines.bill_id:
                            # for bank_line in lines.bill_id.partner_id.bank_ids:
                            #     bank_list.append({
                            #         'bank_name': bank_line.bank_id.name,
                            #         'bank_number': bank_line.acc_number,
                            #         'bank_partner': bank_line.partner_id.name
                            #     })
                            invoice = self.env['account.move'].search([('id', '=', lines.bill_id.id)])
                            vendor = lines.bill_id.partner_id.name or ''
                            purchase_ids = invoice.mapped('line_ids.purchase_line_id.order_id')
                            # id_purchase = int(purchase_ids)
                            purchase = self.env['purchase.order'].search([('id', '=', int(purchase_ids))])

                            if purchase:
                                po_ids.append(purchase.id)
                                po = purchase.name
                                # mrf_ids = []
                                # for purchase_line in purchase:
                                #     if purchase_line.mrf_id:
                                #         mrf_ids.append(purchase_line.mrf_id.id)
                                # mrf_data = self.env['mrf.mrf'].search([('id','in', mrf_ids)])
                                mrf = lines.mrf or ''
                                so = lines.sale_order or ''
                                cust = lines.customer or ''
                                # if purchase.mrf_id:
                                #     mrf = lines.mrf or ''
                                #     so_data = self.env['sale.order'].search(
                                #         [('opportunity_id', '=', purchase.mrf_id.inquiry_id.opportunity_id.id),
                                #          ('state', '=', 'sale')], limit=1)
                                #     if so_data:
                                #         so = lines.sale_order or ''
                                # else:
                                #     mrf = ''
                                #     so = ''
                            else:
                                mrf = ''
                                so = ''
                                po = ''
                        else:
                            vendor = ''
                            mrf = ''
                            po = ''
                else:
                    vendor = ''
                    mrf = ''
                    so = ''
                    po = ''
                purchase_data = self.env['purchase.order'].browse(po_ids)
                currency = purchase_data.currency_id.name or ''
                symbol = currency_id = purchase_data.currency_id.symbol
                for po_lines in purchase_data.order_line:
                    list.append({
                        'product': po_lines.product_id.name,
                        'price_total': po_lines.price_total
                    })
            # for lines in line.request_line_ids:
            #     list.append({
            #         # 'product': lines.product_id.product_tmpl_id.name,
            #         # 'brand': lines.brand,
            #         # 'weight': lines.weight,
            #         # 'supplier': lines.vendor_id.name,
            #         # 'uom': lines.product_uom.name,
            #         # 'qty': lines.quantity,
            #         # 'cost': lines.cost_price,
            #         # 'subtotal': lines.subtotal,
            #     })
            bank_list = [
                {
                    'bank_name': line.bank_name or '',
                    'bank_number': line.bank_number or '',
                    'account_holder': line.account_holder or '',
                }
            ]
            print('account bank', bank_list)
            data = {
                'number': line.name,
                'vendor': vendor,
                'date': str(line.date),
                'due_date': str(line.due_date),
                'mrf': mrf,
                'so': so,
                'po': po,
                'type': type,
                'currency': currency,
                'symbol': symbol,
                'price_dp': price_dp,
                'desc': desc,
                'bank': bank_list,
                'department': line.department_id.name or '',
                'customer': cust or '',
                'item_detail': list,
                'approval_data': line.approval_data()
            }

            return self.env.ref('purchase_custome.action_report_payment_request').with_context(
                paperformat=4, landscape=False).report_action(self, data=data)

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


def action_view_report():
    return {
        "type": "ir.actions.act_window",
        "res_model": "report.budget.project",
        "name": "Generate Report",
        'view_mode': 'form',
        # "context": {"create": False},
        'target': 'new',

    }


class PaymentRequestDp(models.Model):
    _name = 'payment.request.dp'

    order_id = fields.Many2one('purchase.order',
                               domain="[('state','=','purchase'), ('invoice_status','in',['no','to invoice'])]")
    amount_total = fields.Monetary(compute='_compute_amount_totals', currency_field="currency_id")
    percentage = fields.Float()
    currency_id = fields.Many2one('res.currency', compute="_compute_currency")
    amount = fields.Monetary(currency_field="currency_id")
    payment_id = fields.Many2one('payment.request')
    payment_state = fields.Boolean(compute='_compute_payment_state')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], related="payment_id.state")
    customer = fields.Char()
    mrf = fields.Char()
    sale_order = fields.Char()
    purchase_order = fields.Char()

    @api.onchange('order_id')
    def onchange_order_id(self):
        for line in self:
            line.customer = False
            line.mrf = False
            line.sale_order = False
            line.purchase_order = False
            if line.order_id:
                line.purchase_order = line.order_id.name

                if line.order_id.mrf_id:
                    line.mrf = line.order_id.mrf_id.name
                    so_data = self.env['sale.order'].search(
                        [('opportunity_id', '=', line.order_id.mrf_id.inquiry_id.opportunity_id.id),
                         ('state', '=', 'sale')], limit=1)
                    if so_data:
                        line.sale_order = so_data.name
                        line.customer = so_data.partner_id.name

    @api.depends('order_id')
    def _compute_currency(self):
        for line in self:
            line.currency_id = line.order_id.currency_id.id

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
                "res_model": "payment.request.wizard",
                "name": "Create Payment Vendor",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    "create": False,
                    'default_request_payment_id': int(line.id),
                    'default_amount': line.amount,
                    'default_currency_id': line.currency_id.id,
                    'default_partner_id': line.order_id.partner_id.id,
                    # 'default_payment_type': 'outbound',
                    # 'default_partner_type': 'supplier',
                    # 'search_default_outbound_filter': 1,
                    # 'default_move_journal_types': ('bank', 'cash'),
                    # 'display_account_trust': True,
                }
            }
            # return {
            #     "type": "ir.actions.act_window",
            #     "res_model": "account.payment",
            #     "name": "Create Payment Vendor",
            #     'view_mode': 'form',
            #     'target': 'new',
            #     'context': {
            #         "create": False,
            #         'default_request_payment_id': int(line.id),
            #         'default_amount': line.amount,
            #         'default_currency_id': 1,
            #         'default_partner_id': line.order_id.partner_id.id,
            #         'default_payment_type': 'outbound',
            #         'default_partner_type': 'supplier',
            #         'search_default_outbound_filter': 1,
            #         'default_move_journal_types': ('bank', 'cash'),
            #         'display_account_trust': True,
            #     }
            # }

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
                              domain="[('journal_id','=', 2), ('move_type','=', 'in_invoice'), ('state','in', ['draft','posted']), ('payment_state', '!=', 'paid')]")
    amount = fields.Float(compute='_compute_amount')
    bill_status = fields.Boolean(compute="_compute_bill_status")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('validate', 'Validate')
    ], related="payment_id.state")
    customer = fields.Char()
    mrf = fields.Char()
    sale_order = fields.Char()
    purchase_order = fields.Char()
    customer = fields.Char()
    mrf = fields.Char()
    sale_order = fields.Char()
    purchase_order = fields.Char()

    @api.onchange('bill_id')
    def onchange_bill_id(self):
        for line in self:
            line.customer = False
            line.mrf = False
            line.sale_order = False
            line.purchase_order = False
            if line.bill_id:
                invoice = self.env['account.move'].search([('id', '=', line.bill_id.id)])
                vendor = line.bill_id.partner_id.name or 'Unknown'
                purchase_ids = invoice.mapped('line_ids.purchase_line_id.order_id')
                # id_purchase = int(purchase_ids)
                purchase = self.env['purchase.order'].search([('id', '=', int(purchase_ids))])
                if purchase:
                    line.purchase_order = purchase.name
                    if purchase.mrf_id:
                        line.mrf = purchase.mrf_id.name
                        so_data = self.env['sale.order'].search(
                            [('opportunity_id', '=', purchase.mrf_id.inquiry_id.opportunity_id.id),
                             ('state', '=', 'sale')], limit=1)
                        if so_data:
                            line.sale_order = so_data.name
                            line.customer = so_data.partner_id.name

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
