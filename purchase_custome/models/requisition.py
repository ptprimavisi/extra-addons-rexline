from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import date, datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one('purchase.requisition')

    def default_get(self, vals):
        defaults = super(PurchaseOrder, self).default_get(vals)

        # Pastikan Anda memiliki konteks yang menyediakan partner_id
        requisition_id = self.env.context.get('requisition_id', False)
        order_line = self.env.context.get('order_line', False)
        # raise UserError(partner_id)
        if requisition_id and order_line:
            defaults['requisition_id'] = requisition_id
            defaults['order_line'] = order_line
        return defaults

    @api.model
    def create(self, vals):
        new_record = super(PurchaseOrder, self).create(vals)
        requisition_id = new_record.requisition_id
        # raise UserError(requisition_id)
        if requisition_id:
            # Cari record 'purchase.requisition' berdasarkan ID
            requisition = self.env['purchase.requisition'].browse(int(requisition_id))
            if requisition.exists():
                # Ubah status menjadi 'po'
                requisition.state = 'po'
        # vals['name'] = self.env['ir.sequence'].next_by_code('INQ') or '/'
        return new_record


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    responsible = fields.Many2one('res.users', default=lambda self: self.env.user.id)
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env['hr.employee'].search(
        [('user_id', '=', self.env.user.id)]).id)
    department_id = fields.Many2one('hr.department', default=lambda self: self.env['hr.employee'].search(
        [('user_id', '=', self.env.user.id)]).department_id.id)
    requisition_date = fields.Date(default=lambda self: datetime.now())
    purpose = fields.Char()
    due_date = fields.Date()
    ref = fields.Char()
    is_ga = fields.Boolean(compute='_compute_ga')
    is_purchase = fields.Boolean(compute='_compute_purchase')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'To Confirm'),
        ('ready', 'Confirm'),
        ('to_purchase', 'Process to Purchase'),
        ('po', 'Purchase Order Created'),
        ('cancel', 'Cancel'),
    ], default="confirm")
    requisition_line = fields.One2many('requisition.line', 'requisition_id')
    count_po = fields.Integer(compute='_compute_count_po')
    count_quotation = fields.Integer(compute='_compute_count_quotation')
    category = fields.Selection([
        ('ga', 'GA'),
        ('ut', 'IT'),
    ], default="ga")
    akses_quot = fields.Boolean(compute="_akses_quot")
    akses_proccess = fields.Boolean(compute="_akses_proccess")
    it_id = fields.Many2one('it.request')
    date_confirm = fields.Date()
    date_approved1 = fields.Date(compute="_compute_approved1")
    date_approved2 = fields.Date(compute="_compute_approved2")
    create_employee_id = fields.Many2one('hr.employee', compute="_compute_employee_created", store=True)
    active = fields.Boolean(default=True)

    def _compute_employee_created(self):
        for line in self:
            line.create_employee_id = False
            if line.create_uid:
                employee_id = self.env['hr.employee'].search([('user_id','=',line.create_uid.id)])
                if employee_id:
                    line.create_employee_id = int(employee_id.id)

    def _compute_approved1(self):
        for line in self:
            line.date_approved1 = False
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
            if approval:
                multi_approval_line = self.env['multi.approval.line'].search(
                    [('approval_id', '=', int(approval.id))])
                if multi_approval_line and len(multi_approval_line) > 1:
                    if multi_approval_line[0].state == 'Approved':
                        line.date_approved1 = multi_approval_line[0].write_date.strftime('%Y-%m-%d')
                if len(multi_approval_line) == 1:
                    if multi_approval_line.state == 'Approved':
                        line.date_approved1 = multi_approval_line.write_date.strftime('%Y-%m-%d')

    def _compute_approved2(self):
        for line in self:
            line.date_approved2 = False
            model_name = self._name
            active_id = int(line.id)
            origin_ref = f"{model_name},{active_id}"
            approval = self.env['multi.approval'].search([('origin_ref', '=', origin_ref)])
            if approval:
                multi_approval_line = self.env['multi.approval.line'].search(
                    [('approval_id', '=', int(approval.id))])
                if multi_approval_line and len(multi_approval_line) > 1:
                    if multi_approval_line[1].state == 'Approved':
                        line.date_approved2 = multi_approval_line[1].write_date.strftime('%Y-%m-%d')

    def action_print(self):
        return self.env.ref('custom_report.action_report_requisition').with_context(
            paperformat_id=10, landscape=True).report_action(self)

    def write(self, vals):
        res = super(PurchaseRequisition, self).write(vals)
        for record in self:
            if 'x_review_result' in vals:
                x_result = record.x_review_result
                if x_result == 'approved':
                    vals['state'] = 'to_purchase'
        res = super(PurchaseRequisition, self).write(vals)
        return res

    def _akses_quot(self):
        for line in self:
            line.akses_quot = True
            if line.state == 'to_purchase':
                if not self.env.user.has_group('sale_custome.purchasing_custom_group'):
                    line.akses_quot = False
            if line.state == 'ready' and line.category == 'ga':
                if not self.env.user.has_group('sale_custome.hr_ga_custom_group'):
                    line.akses_quot = False
            if line.state == 'ready' and line.category == 'ut':
                if not self.env.user.has_group('sale_custome.it_custom_group'):
                    line.akses_quot = False

    def _akses_proccess(self):
        for line in self:
            line.akses_proccess = True
            if line.state == 'ready' and line.category == 'ga':
                if not self.env.user.has_group('sale_custome.hr_ga_custom_group'):
                    line.akses_proccess = False
            if line.state == 'ready' and line.category == 'ut':
                if not self.env.user.has_group('sale_custome.it_custom_group'):
                    line.akses_proccess = False

    # users_branch = fields.Char(compute="branch", search="branch_search")
    #
    # #
    # def branch(self):
    #     id = self.env.uid
    #     self.users_branch = self.env['res.users'].search([('id', '=', id)])
    #
    # #
    # def branch_search(self, operator, value):
    #     # for i in self:
    #     # if self.env.user.has_group('sale_custome.hr_ga_custom_group'):
    #     #     pr = self.env['purchase.requisition'].search([('category', '=', 'ga')])
    #     #
    #     #     # print('lihat employee', contract.id)
    #     #     domain = [('id', 'in', pr.ids)]
    #     # if self.env.user.has_group('sale_custome.it_custom_group'):
    #     #     pr = self.env['purchase.requisition'].search([('category', '=', 'ut')])
    #     #
    #     #     # print('lihat employee', contract.id)
    #     #     domain = [('id', 'in', pr.ids)]
    #     # if self.env.user.has_group('sale_custome.hr_ga_custom_group') and self.env.user.has_group('sale_custome.it_custom_group'):
    #     #     pr = self.env['purchase.requisition'].search([('category', 'in', ['ut','ga'])])
    #     #
    #     #     # print('lihat employee', contract.id)
    #     #     domain = [('id', 'in', pr.ids)]
    #     # if self.env.user.has_group('sale_custome.purchasing_custom_group'):
    #     #     pr = self.env['purchase.requisition'].search([('category', 'in', ['ut','ga'])])
    #     #
    #     #     # print('lihat employee', contract.id)
    #     #     domain = [('id', '!=', False)]
    #     # else:
    #     # pr = self.env['purchase.requisition'].search([('responsible', '=', self.env.uid)])
    #     domain = [('id', '!=',False)]
    #
    #     return domain

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves['name'] = self.env['ir.sequence'].next_by_code('EPR')
        return moves

    def _compute_count_po(self):
        for line in self:
            purchase = self.env['purchase.order'].search(
                [('requisition_id', '=', int(line.id)), ('state', '=', 'purchase')])
            line.count_po = 0
            if purchase:
                line.count_po = len(purchase)

    def _compute_count_quotation(self):
        for line in self:
            purchase = self.env['purchase.order'].search(
                [('requisition_id', '=', int(line.id)), ('state', '=', 'draft')])
            line.count_quotation = 0
            if purchase:
                line.count_quotation = len(purchase)

    def action_count_po(self):
        purchase = self.env['purchase.order'].search(
            [('requisition_id', '=', int(self.id)), ('state', '=', 'purchase')])
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "domain": [('id', 'in', purchase.ids)],
            "context": {"create": False},
            "name": "Purchase Order",
            'view_mode': 'tree,form',
        }

    def action_count_quotation(self):
        purchase = self.env['purchase.order'].search(
            [('requisition_id', '=', int(self.id)), ('state', '=', 'draft')])
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "domain": [('id', 'in', purchase.ids)],
            "context": {"create": False},
            "name": "Purchase Order",
            'view_mode': 'tree,form',
        }

    def action_confirm(self):
        for line in self:
            req = self.env['purchase.requisition'].browse(int(line.id))
            req.write({'state': 'ready'})
            line.date_confirm = datetime.today()

    def action_to_purchase(self):
        for line in self:
            req = self.env['purchase.requisition'].browse(int(line.id))
            req.write({'state': 'to_purchase'})

    def action_create_po(self):
        for line in self:
            req = self.env['purchase.requisition'].browse(int(line.id))
            req.write({'state': 'po'})

    def _compute_ga(self):
        for line in self:
            line.is_ga = False
            users = self.env['res.users'].browse(self.env.uid)
            if users.is_ga:
                line.is_ga = True

    def _compute_purchase(self):
        for line in self:
            line.is_purchase = False
            users = self.env['res.users'].browse(self.env.uid)
            if users.is_purchase:
                line.is_purchase = True

    def action_create_quotation(self):
        for line in self:
            list_prod = []
            for lines in line.requisition_line:
                if lines.select:
                    list_prod.append((0, 0, {
                        'product_id': lines.product_id.id,
                        'product_qty': lines.quantity,
                        'price_unit': lines.price_unit,
                        'product_uom': lines.product_uom.id
                    }))

            if list_prod:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Requests for Quotation',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'requisition_id': int(line.id),
                        'order_line': list_prod
                    }
                }
            else:
                raise UserError('Product Not Found')


class RequisitionLine(models.Model):
    _name = 'requisition.line'

    select = fields.Boolean(default=True)
    approve = fields.Boolean(default=True)
    product_id = fields.Many2one('product.product')
    type = fields.Char()
    product_request = fields.Char()
    name = fields.Char()
    quantity = fields.Float(default=1)
    qty_purchase = fields.Float(default=1)
    qty_ordered = fields.Float(compute="_compute_qty_ordered")
    qty_received = fields.Float(compute="_compute_qty_received")
    product_uom = fields.Many2one('uom.uom', compute="_default_product_uom", readonly=False, precompute=True)
    price_unit = fields.Float(compute="_default_price_unit", readonly=False, precompute=True)
    subtotal = fields.Float(compute='_compute_subtotal')
    requisition_id = fields.Many2one('purchase.requisition')
    is_it = fields.Boolean(compute="_compute_is_it")
    brand = fields.Char()
    remark = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'To Confirm'),
        ('ready', 'Confirm'),
        ('to_purchase', 'Process to Purchase'),
        ('po', 'Purchase Order Created'),
        ('cancel', 'Cancel'),
    ], related="requisition_id.state")

    # state = fields.Char(related="requisition_id.state")

    @api.onchange('quantity')
    def onchange_qty(self):
        for line in self:
            line.qty_purchase = 0
            if line.quantity:
                line.qty_purchase = line.quantity

    def _compute_qty_ordered(self):
        for line in self:
            purchase = self.env['purchase.order.line'].search(
                [('order_id.requisition_id', '=', int(line.requisition_id.id)), ('state', '=', 'purchase'),
                 ('product_id', '=', line.product_id.id)])
            line.qty_ordered = sum(purchase.mapped('product_qty'))

    def _compute_qty_received(self):
        for line in self:
            purchase = self.env['purchase.order.line'].search(
                [('order_id.requisition_id', '=', int(line.requisition_id.id)), ('order_id.state', '=', 'purchase'),
                 ('product_id', '=', line.product_id.id)])
            # print(purchase)
            line.qty_received = sum(purchase.mapped('qty_received'))

    def _compute_is_it(self):
        for line in self:
            line.is_it = False
            if line.requisition_id.category == 'ut':
                if self.env.user.has_group('sale_custome.it_custom_group'):
                    line.is_it = True
            if line.requisition_id.category == 'ga':
                if self.env.user.has_group('sale_custome.hr_ga_custom_group'):
                    line.is_it = True

    @api.onchange('approve')
    def onchange_approve(self):
        for line in self:
            line.select = line.approve

    @api.depends('product_id')
    def _default_product_uom(self):
        for line in self:
            if line.product_id:
                line.product_uom = line.product_id.uom_po_id.id

    @api.depends('product_id')
    def _default_price_unit(self):
        for line in self:
            line.price_unit = line.product_id.standard_price

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            total = line.quantity * line.price_unit
            line.subtotal = total
