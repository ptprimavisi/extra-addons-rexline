from abc import ABC

from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta

AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'High'),
    ('3', 'Very High'),
]


# class ProductTemplateInherith(models.Model):
#     _inherit = 'product.template'

#     weight = fields.Float()

class inheritAccountMove(models.Model):
    _inherit = 'account.move'

    source_invoice = fields.Many2one(
        'account.move',
        string="Source Invoice"
    )

    is_credit_note = fields.Boolean()

    def action_post(self):
        for rec in self:
            if rec.move_type == 'out_refund' and not rec.source_invoice:
                raise UserError('Source Invoice must be filled.')
            else:
                return super(inheritAccountMove, rec).action_post()

    @api.model
    def create(self, vals):
        if vals.get('move_type') and vals['move_type'] == 'our_refund':
            if vals.get('source_invoice'):
                source_invoice_id = vals['source_invoice']

                credit_notes = self.env['account.move'].search([
                    ('move_type', '=', 'out_refund'),
                    ('state', '!=', 'cancel'),
                    ('source_invoice', '!=', False)
                ])
                credit_note_names = credit_notes.mapped('name')

                used_invoice_ids = credit_notes.mapped('source_invoice.id')
                source_invoice = self.env['account.move'].browse(source_invoice_id)

                if source_invoice.id not in used_invoice_ids:
                    source_invoice.write({'is_credit_note': True})
                else:
                    raise UserError(
                        f'Invoice {source_invoice.name} has already been used in credit notes: {", ".join(credit_note_names)}')

        return super(inheritAccountMove, self).create(vals)

    @api.model
    def write(self, vals):
        if vals.get('source_invoice'):
            source_invoice_id = vals['source_invoice']

            credit_notes = self.env['account.move'].search([
                ('move_type', '=', 'out_refund'),
                ('state', '!=', 'cancel'),
                ('source_invoice', '!=', False)
            ])
            credit_note_names = credit_notes.mapped('name')

            used_invoice_ids = credit_notes.mapped('source_invoice.id')
            source_invoice = self.env['account.move'].browse(source_invoice_id)

            if source_invoice.id not in used_invoice_ids:
                source_invoice.write({'is_credit_note': True})
            else:
                raise UserError(
                    f'Invoice {source_invoice.name} has already been used in credit notes: {", ".join(credit_note_names)}')

        return super(inheritAccountMove, self).write(vals)

    def action_reverse(self):
        for rec in self:
            used_invoice_ids = self.env['account.move'].search([
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('source_invoice', '=', rec.id)
            ])
            credit_note_names = used_invoice_ids.mapped('name')
            if used_invoice_ids:
                raise UserError(
                    f'Invoice {rec.name} has already been used in credit notes: {", ".join(credit_note_names)}')
            else:
                return super(inheritAccountMove, rec).action_reverse()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            rec.source_invoice = False

    @api.onchange('source_invoice')
    def _onchange_source_invoice(self):
        for rec in self:
            if rec.source_invoice:
                used_invoice_ids = self.env['account.move'].search([
                    ('move_type', '=', 'out_refund'),
                    ('state', '=', 'posted'),
                    ('source_invoice', '=', rec.source_invoice.id)
                ])
                credit_note_names = used_invoice_ids.mapped('name')
                if used_invoice_ids:
                    raise UserError(
                        f'Invoice {rec.source_invoice.name} has already been used in credit notes: {", ".join(credit_note_names)}')


class MailActivity(models.TransientModel):
    _inherit = 'mail.activity.schedule'


class MrpProductionInherith(models.Model):
    _inherit = 'mrp.production'

    count_report = fields.Integer(compute="_compute_count_report")

    def button_mark_done(self):
        for liine in self:
            report = self.env['production.report'].search([('mo_id', '=', int(liine.id))])
            if report:
                for liiness in report:
                    if liiness.state == 'draft':
                        raise UserError('Selesaikan Schedule Activity Terlrbih Dahulu!')
                        exit()
        res = super(MrpProductionInherith, self).button_mark_done()
        return res

    def action_compute_consume(self):
        for line in self:
            for lines in line.move_raw_ids:
                lines.quantity = 0
                report_line = self.env['production.report.line'].search(
                    [('production_id.mo_id', '=', int(line.id)), ('product_id', '=', lines.product_id.id),
                     ('state', '=', 'done')])
                if report_line:
                    jumlah = 0
                    for consume in report_line:
                        jumlah += consume.qty_consume

                    lines.quantity = jumlah

    def action_count_report(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "production.report",
                "domain": [('mo_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "Progress",
                'view_mode': 'tree,form',
            }

    def _compute_count_report(self):
        for line in self:
            count = 0
            report = self.env['production.report'].search([('mo_id', '=', int(line.id))])
            for lines in report:
                count += 1
            line.count_report = count

    def action_create_schedule(self):
        for line in self:
            list = []
            for lines in line.move_raw_ids:
                list.append((0, 0, {
                    'product_id': lines.product_id.id,
                    'raw_id': int(lines.id)
                    # 'qty_to_consume': lines.product_uom_qty
                }))
            return {
                "type": "ir.actions.act_window",
                "res_model": "schedule.wizard",
                # "context": {"create": False},
                "name": "Schedule Wizard",
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'product_id': int(line.product_id.id),
                    'mo_id': int(line.id),
                    'production_line_ids': list
                }
            }
            # return {
            #     "type": "ir.actions.act_window",
            #     "res_model": "production.report",
            #     # "context": {"create": False},
            #     "name": "Schedule progress",
            #     'view_mode': 'form',
            #     'target': 'new',
            #     'context': {
            #         'product_id': int(line.product_id.id),
            #         'mo_id': int(line.id),
            #         'production_line_ids': list
            #     }
            # }


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    inquiry_id = fields.Many2one('inquiry.inquiry')
    request_state = fields.Boolean(default=False)
    state_cost = fields.Selection([
        ('empty', 'Cost Is Empty'),
        ('request', 'Send Request'),
        ('ready', 'Ready')
    ], compute="_compute_state_cost", readonly=False, precompute=True)

    def _compute_state_cost(self):
        for line in self:
            master = line.product_tmpl_id.id
            if master:
                material = self.env['mrp.bom.line'].search(
                    [('bom_id', '=', line.id), ('product_id.product_tmpl_id.standard_price', '=', 0.0)])
                if material or line.product_tmpl_id.standard_price == 0:
                    # raise UserError(material)
                    # ck_price_count = len(material)
                    # if ck_price_count > 0:
                    line.state_cost = 'empty'
                    if line.request_state:
                        line.state_cost = 'request'
                else:
                    line.state_cost = 'ready'

            else:
                line.state_cost = 'empty'

    def action_request_price(self):
        for line in self:
            rp = self.env['request.price'].search([])
            list_line = []
            for lines in line.bom_line_ids:
                product = self.env['product.template'].search(
                    [('id', '=', int(lines.product_tmpl_id.id)), ('standard_price', '=', 0)])
                if product:
                    list_line.append((0, 0, {
                        'product_id': lines.product_id.id
                    }))

                # else:
                #     raise UserError('Product not found')

            data = {
                'bom_id': int(line.id),
                'date': datetime.now().strftime("%Y-%m-%d"),
                'request_line_ids': list_line
            }
            # print(data)
            # exit()
            rp.create(data)
            bom = self.env['mrp.bom'].browse(int(line.id))
            bom.write({'request_state': True})

    def default_get(self, vals):
        defaults = super(MrpBom, self).default_get(vals)

        # Pastikan Anda memiliki konteks yang menyediakan partner_id
        inquiry_id = self.env.context.get('inquiry_id', False)
        # raise UserError(partner_id)
        if inquiry_id:
            defaults['inquiry_id'] = inquiry_id

        return defaults


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    # def default_get(self, fields_list):
    #     defaults = super(MrpProduction, self).default_get(fields_list)
    #
    #     product_id = self.env.context.get('product_id', False)
    #     product_qty = self.env.context.get('product_qty', False)
    #     origin = self.env.context.get('origin', False)
    #     state = self.env.context.get('state', False)
    #     if origin:
    #         # defaults['product_id'] = [('id', '=', product_id)]
    #         defaults['product_id'] = product_id
    #         defaults['product_qty'] = product_qty
    #         defaults['origin'] = origin
    #         # defaults['state'] = state
    #
    #     return defaults


import json


class SaleOrderInherith(models.Model):
    _inherit = 'sale.order'

    validity = fields.Date()
    ref_quotation = fields.Char()
    count_estimate = fields.Integer(compute="_compute_count_estimate")
    tax_list = fields.Char(compute="_compute_tax_list")

    def report_ar(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Report Account Receiptable',
            'res_model': 'report.ar',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('order_line')
    def _compute_tax_list(self):
        # raise UserError('test')
        for line in self:
            list = []
            if line.order_line:
                tax_ids = []
                for lines in line.order_line:
                    if lines.tax_id:
                        for line_tax in lines.tax_id:
                            tax_ids.append(line_tax.id)
                tax_data = self.env['account.tax'].search([('id', 'in', tuple(tax_ids))])
                for datas in tax_data:
                    amount = self.amount_by_tax(int(line.id), [datas.id])
                    list.append({
                        'name': f"Taxes ({datas.name})",
                        'amount': amount
                    })
            for item in list:
                item['formatted_amount'] = str(line.currency_id.symbol) + '{:,.2f}'.format(item['amount'])
            line.tax_list = json.dumps(list)

            # line.tax_list = str(tax_data)

    def amount_by_tax(self, order_id, tax_id):
        data = self.env['sale.order.line'].search([('order_id', '=', order_id), ('tax_id', 'in', tax_id)])
        tax = self.env['account.tax'].search([('id', 'in', tax_id)])
        amount = 0
        for line in data:
            total = (line.price_unit * line.product_uom_qty) * tax.amount / 100
            amount += total
        return amount

    def action_print_report(self):
        for line in self:
            # raise UserError(line.tax_list)
            return self.env.ref('sale_custome.action_report_quotation').with_context(
                paperformat=4, landscape=False).report_action(self)

    def action_view_estimate(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "inquiry.estimate",
                "domain": [('sale_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "Estimate",
                'view_mode': 'tree,form',
            }

    def _compute_count_estimate(self):
        for line in self:
            c = 0
            estimate = self.env['inquiry.estimate'].search([('sale_id', '=', int(line.id))])
            for i in estimate:
                c += 1
            line.count_estimate = c

    # def action_confirm(self):
    #     for line in self:
    #         if hasattr(line, 'x_review_result') and hasattr(line, 'x_has_request_approval'):
    #             if line.x_has_request_approval:
    #                 line.name = self.env['ir.sequence'].next_by_code('SOC') or '/'
    def action_confirm(self):
        # Tambahkan logika atau kondisi khusus di sini
        for order in self:
            order.ref_quotation = order.name
            order.name = self.env['ir.sequence'].next_by_code('SOC') or '/'

            # if hasattr(order, 'x_review_result') and hasattr(order, 'x_has_request_approval'):
            #     if order.x_has_request_approval:

        # Panggil implementasi asli dari action_confirm
        res = super(SaleOrderInherith, self).action_confirm()

        # Tambahkan logika tambahan setelah pemanggilan `super()` jika diperlukan
        # ...

        return res

    def copy(self, default=None):
        # Set default to an empty dictionary if not provided
        default = dict(default or {})

        # Add custom default values or modify existing ones
        original_name = self.name

        # Cek apakah sudah ada duplikat sebelumnya dengan pola nama yang sama
        existing_copies = self.env['sale.order'].search([('name', 'like', original_name + '_Duplicate %')])

        # Tentukan nomor urut yang akan digunakan
        if existing_copies:
            # Ambil nomor terbesar dari duplikat yang ada
            last_number = max([
                int(name.split('_Duplicate ')[-1])
                for name in existing_copies.mapped('name')
                if name.split('_Duplicate ')[-1].isdigit()
            ])
            next_number = last_number + 1
        else:
            next_number = 1

        # Setel nama baru dengan nomor urut berikutnya
        new_name = f"{original_name}_Duplicate {next_number}"
        default['name'] = new_name

        # You can also exclude fields from being copied or reset fields
        # default.pop('field_name_to_reset', None)

        # Call the parent class's copy method to perform the actual duplication
        return super(SaleOrderInherith, self).copy(default)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    count_inquiry = fields.Integer(compute="_compute_count_inquiry")
    cost_estimation = fields.Float(compute="_compute_estimation_cost")
    is_planner = fields.Boolean(compute="_compute_is_planner")
    state_inquiry = fields.Char(compute="_compute_state_inq")
    is_approve = fields.Boolean(compute="_compute_isApprove")
    status_estimate = fields.Boolean(default=False)
    process_to = fields.Selection([
        ('purchase', 'Purchase'),
        ('engineering', 'Engineering')
    ])
    warning_time = fields.Selection([
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('green', 'Green')
    ], compute="_compute_warning")

    def _compute_isApprove(self):
        for line in self:
            line.is_approve = False
            if hasattr(line, 'x_review_result') and hasattr(line, 'x_has_request_approval'):
                if line.x_review_result and line.x_has_request_approval:
                    line.is_approve = True

    @api.depends('date_deadline')
    def _compute_warning(self):
        for line in self:
            line.warning_time = False
            if line.date_deadline:
                due_date = datetime.strptime(str(line.date_deadline), '%Y-%m-%d')
                two_days_before_due = due_date - timedelta(days=2)
                five_days_before_due = due_date - timedelta(days=5)
                # after_days_before_due = due_date - datetime.timedelta(days=2)
                today = datetime.today()
                if today >= two_days_before_due:
                    line.warning_time = 'red'
                if five_days_before_due <= today < two_days_before_due:
                    line.warning_time = 'yellow'
                if today < five_days_before_due:
                    line.warning_time = 'green'

    @api.onchange('process_to')
    def rmove_pic(self):
        for line in self:
            if line.process_to == 'engineering':
                line.pic_supply = False

    @api.onchange('category_project')
    def rmove_pic(self):
        for line in self:
            if line.category_project != 'supply':
                line.process_to = False

    pic_supply = fields.Many2one('res.users')
    group_ids = fields.Many2one('res.groups', compute="_compute_group")

    def action_approve_cost_estimation(self):
        for line in self:
            line.is_approve = True
            message = f'Approve cost estimtion'
            line.message_post(body=message)

    def _compute_group(self):
        for line in self:
            groups = self.env.ref('sale_custome.purchasing_custom_group')
            # raise UserError(groups.name)
            line.group_ids = groups.id

    # @api.onchange('process_to')
    # def action_pic(self):
    #     for line in self:
    #         if line.process_to:
    #             groups = self.env.ref('sales_team.group_sale_salesman')
    #             domain = [('groups_id', '=', groups.id)]
    #             return {'domain': {'pic_supply': domain}}

    def get_selection_label(self, model, field_name, value):
        """Get the label of a selection field."""
        selection = self.env[model]._fields[field_name].selection
        if selection:
            for key, label in selection:
                if key == value:
                    return label

    def write(self, vals):
        for record in self:
            old_category_value = record.category_project
            old_note = record.description

            # Panggil metode 'write' dari superclass
        res = super(CrmLead, self).write(vals)

        # Ambil nilai field 'category' setelah pembaruan
        for record in self:
            new_category_value = record.category_project
            new_note = record.description

            # Cek apakah nilai 'category' berubah
            if old_category_value != new_category_value:
                message = f'Category value changed from {old_category_value} to {new_category_value}'
                record.message_post(body=message)
            inquiry = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(record.id))])
            if record.note_header:
                inquiry = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(record.id))])
                inquiry.write({'header_note': record.note_header})
            # raise UserError('test')
            if inquiry:
                inquiry.write({'due_date': record.date_deadline})
                if old_note != new_note:
                    user = self.env['res.users'].browse(self.env.uid)
                    inquiry.message_post(body=f'{user.login} Update Note')

        return res

    # def write(self, vals):
    #     res = super(IrActions, self).write(vals)
    #     # self.get_bindings() depends on action records
    #     self.env.registry.clear_cache()
    #     return res

    def _compute_state_inq(self):
        for line in self:
            line.state_inquiry = 'no inquiry'
            inquiry = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))])
            if inquiry:
                state_value = inquiry.state
                state_label = self.get_selection_label('inquiry.inquiry', 'state', state_value)
                line.state_inquiry = str(state_label)

    def _compute_is_planner(self):
        for line in self:
            uid = self.env.uid
            user = self.env['res.users'].browse(int(uid))
            line.is_planner = False
            if user.is_planner:
                line.is_planner = True

    @api.depends('lead_product_detail.subtotal')
    def _compute_estimation_cost(self):
        for line in self:
            cost = 0
            if line.category_project:
                if line.category_project == 'project' or line.category_project == 'service':
                    for lines in line.lead_product_detail:
                        cost += lines.subtotal
                    line.cost_estimation = cost
                if line.category_project == 'supply':
                    cost_master = 0
                    for liness in line.lead_product_ids:
                        cost_master += liness.cost_price * liness.product_uom_quantity
                    line.cost_estimation = cost_master
            else:
                line.cost_estimation = cost

    def _compute_count_inquiry(self):
        for line in self:
            line.count_inquiry = 0
            inquiry = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))])
            if inquiry:
                for liness in inquiry:
                    print(liness)
                    line.count_inquiry += 1

    def process_attachments(self):
        for record in self:
            attachments = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', record.id)])
            return attachments

    def action_view_inquiry(self):
        # self.process_attachments()
        # exit()
        for line in self:
            inquiry = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))])
            if inquiry:
                list = len(inquiry)
                # raise UserError(list)
                # list = 0
                # # for liness in inquiry:
                #     list += 1
                if list == 1:
                    inquiry_record = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))],
                                                                        limit=1)
                    result = {
                        "type": "ir.actions.act_window",
                        "res_model": "inquiry.inquiry",
                        "domain": [('opportunity_id', '=', int(line.id))],
                        "context": {"create": False},
                        "name": "Inquiry",
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_id': inquiry_record.id
                    }

                elif list > 1:
                    result = {
                        "type": "ir.actions.act_window",
                        "res_model": "inquiry.inquiry",
                        "domain": [('opportunity_id', '=', int(line.id))],
                        "context": {"create": False},
                        "name": "Inquiry",
                        'view_mode': 'tree,form',
                    }
                return result
            else:
                pass

    def action_send_inquiry(self):
        for line in self:
            if not line.category_project:
                raise UserError('project category is empty!')
            if not line.id:
                raise UserError('ID CRM tidak ditemukan')
            else:
                data = {
                    "partner_id": line.partner_id.id,
                    'project_category': line.category_project,
                    'header_note': line.note_header,
                    "due_date": line.date_deadline,
                    "date": datetime.now(),
                    "opportunity_id": int(line.id),
                    "priority": line.priority,
                    "note": line.description
                }
                # if line.category_project == 'supply':
                #     data['process_to'] = line.process_to
                # inquiry = self.env['inquiry.inquiry'].search([])
                inquiry = self.env['inquiry.inquiry'].create(data)
                if line.category_project == 'supply' or line.category_project == 'project':
                    list_product = []
                    if not line.lead_product_ids:
                        raise UserError('Pl add product first')
                    for lines in line.lead_product_ids:
                        list_product.append((0, 0, {
                            'product_id': lines.product_id.id,
                            'name': lines.name or '',
                            'product_uom_quantity': lines.product_uom_quantity,
                            'product_uom': lines.product_uom.id,
                            'unit_weight': lines.product_id.product_tmpl_id.weight,
                            'cost_price': lines.product_id.product_tmpl_id.standard_price
                        }))
                    inquiry.write({'inquiry_line_detail': list_product})
                    # if line.process_to == 'purchase':
                    #     if line.pic_supply:
                    #         inquiry.write({'pic_user': line.pic_supply})
                    # line.pic_user = line.pic_supply
                # if line.category_project == 'supply' and line.process_to == 'engineering':
                #     list_product = []
                #     if not line.lead_product_ids:
                #         raise UserError('Pl add product first')
                #     for lines in line.lead_product_ids:
                #         list_product.append((0, 0, {
                #             'product_id': lines.product_id.id,
                #             'name': lines.name or '',
                #             'product_uom_quantity': lines.product_uom_quantity,
                #             'product_uom': lines.product_uom.id,
                #             'unit_weight': lines.product_id.product_tmpl_id.weight,
                #             'cost_price': lines.product_id.product_tmpl_id.standard_price
                #         }))
                #     inquiry.write({'inquiry_line_detail': list_product})
                # raise UserError(inquiry)
                attch = self.process_attachments()
                if attch:
                    attachments = self.env['ir.attachment'].search([])
                    for attch_line in attch:
                        datass = {
                            'name': attch_line.name,
                            'datas': attch_line.datas,  # Binary data attachment
                            # 'datas_fname': attch_line.datas_fname,  # File name of attachment
                            'res_model': 'inquiry.inquiry',  # Model name of sale.order
                            'res_id': int(inquiry.id),
                            'type': 'binary',  # ID of the sale.order record
                            # Add other required fields for the attachment
                        }
                        self.env['ir.attachment'].create(datass)
                        # attachments.create({
                        #     'res_id': int(inquiry.id),
                        #     'company_id': attch_line.company_id.id,
                        #     'file_size': attch_line.file_size,
                        #     'create_uid': attch_line.create_uid.id,
                        #     'name': attch_line.name or '',
                        #     'res_model': 'inquiry.inquiry',
                        #     'type': attch_line.type,
                        #     'store_fname': attch_line.store_fname,
                        #     'checksum': attch_line.checksum,
                        #     'mimetype': attch_line.mimetype,
                        #     'index_content': attch_line.index_content
                        #
                        # })
                # result = {
                #     "type": "ir.actions.act_window",
                #     "res_model": "rfq.rfq",
                #     "domain": [('opportunity_id', '=', int(line.id))],
                #     "context": {"create": False},
                #     "name": "RFQ",
                #     'view_mode': 'tree,form',
                # }
                # return result


class InquirySales(models.Model):
    _name = 'inquiry.inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(readonly=True)
    partner_id = fields.Many2one('res.partner')
    note = fields.Html()
    date = fields.Date()
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('boq', 'BOQ'),
        ('request', 'Price Request'),
        ('cost', 'Cost Estimation'),
        ('won', 'Won'),
        ('done', 'Material Request'),
        ('cancel', 'Cancel')
    ], default='draft')
    count_rfq = fields.Integer(compute="_compute_count_rfq")
    state_count_rfq = fields.Boolean(compute="_compute_state_count")
    project_category = fields.Selection([
        ('project', 'Project'),
        ('service', 'Service'),
        ('supply', 'Supply')
    ])
    priority = fields.Selection(AVAILABLE_PRIORITIES, select=True)
    opportunity_id = fields.Many2one('crm.lead')
    count_bom = fields.Integer(compute="_compute_use_bom")
    count_mrf = fields.Integer(compute="_compute_use_mrf")
    state_material = fields.Boolean(compute="_compute_state_mrf")
    count_so = fields.Integer(compute="_compute_count_so")
    mrp_production_count = fields.Integer(compute="_compute_mo_count")
    count_rfp = fields.Integer(compute="_compute_count_rfp")
    due_date = fields.Datetime(default=lambda self: fields.Datetime.today() + timedelta(days=1))
    operation_type = fields.Selection([
        ('project', 'Project'),
        ('wo', 'Work Order')
    ])
    crm_state = fields.Char(compute="_compute_state_crm")
    inquiry_line_detail = fields.One2many('inquiry.line.detail', 'inquiry_id')
    inquiry_line_ids = fields.One2many('inquiry.line', 'inquiry_id')
    inquiry_line_task = fields.One2many('inquiry.line.task', 'inquiry_id')
    pic_user = fields.Many2one('res.users', domain=[('is_engineering', '=', True)])
    pic_akses = fields.Boolean(compute="_compute_akses_pic")
    is_planner = fields.Boolean(compute="_compute_user_planner")
    total_amount = fields.Float(compute="_compute_total_cost")
    count_inquiry_log = fields.Integer(compute="_compute_count_log")
    process_to = fields.Selection([
        ('purchase', 'Purchase'),
        ('engineering', 'Engineering')
    ])
    header_note = fields.Text()
    approve_mng_engineer = fields.Boolean()
    sale_id = fields.Many2one('sale.order', compute="compute_saleorder")

    def compute_saleorder(self):
        for line in self:
            line.sale_id = False
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', line.opportunity_id.id), ('state', '=', 'sale')],
                limit=1)
            if so:
                line.sale_id = int(so.id)

    def _compute_count_log(self):
        for line in self:
            count = 0
            inquiry = self.env['log.inquiry'].search([('inquiry_id', '=', int(line.id))])
            if inquiry:
                for lines in inquiry:
                    count += 1

            line.count_inquiry_log = count

    def action_count_log(self):
        for line in self:
            result = {
                "type": "ir.actions.act_window",
                "res_model": "log.inquiry",
                "domain": [('inquiry_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "Revisi Inquiry",
                'view_mode': 'tree,form',
            }
            return result

    @api.depends('inquiry_line_detail.subtotal')
    def _compute_total_cost(self):
        for line in self:
            cost = 0
            for lines in line.inquiry_line_detail:
                cost += lines.subtotal
            line.total_amount = cost

    def unlink(self):
        for line in self:
            inquiry_line = self.env['inquiry.line'].search([('inquiry_id', '=', int(line.id))])
            inquiry_line_detail = self.env['inquiry.line.detail'].search([('inquiry_id', '=', int(line.id))])
            inquiry_line_task = self.env['inquiry.line.task'].search([('inquiry_id', '=', int(line.id))])
            if inquiry_line:
                inquiry_line.unlink()
            if inquiry_line_detail:
                inquiry_line_detail.unlink()
            if inquiry_line_task:
                inquiry_line_task.unlink()
            request_price = self.env['request.price'].search([('inquiry_id', '=', int(line.id))])
            if request_price:
                request_price.unlink()
            mrf = self.env['mrf.mrf'].search([('inquiry_id', '=', int(line.id))])
            if mrf:
                mrf.unlink()
                # raise UserError('Tidak dapat menghapus dokumen, Status Posted!')
        return super().unlink()

    def _compute_user_planner(self):
        for line in self:
            line.is_planner = False
            uid = self.env.uid
            user = self.env['res.users'].browse(uid)
            if user.is_planner == True:
                line.is_planner = True

    def _compute_akses_pic(self):
        for line in self:
            user_id = self.env.uid
            line.pic_akses = False
            if line.pic_user:
                if user_id == int(line.pic_user.id):
                    line.pic_akses = True

    def _compute_state_crm(self):
        for line in self:
            line.crm_state = 'To Quotations'
            quotation = self.env['sale.order'].search(
                [('opportunity_id', '=', int(line.opportunity_id.id)), ('state', '=', 'draft')])
            if quotation:
                line.crm_state = 'Quotations'
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', int(line.opportunity_id.id)), ('state', '=', 'sale')])
            if so:
                line.crm_state = 'Sale Order'

    def action_mark_won(self):
        for line in self:
            line.state = 'won'

    def action_reset_toboq(self):
        for line in self:
            log_inq = self.env['log.inquiry'].search([])
            bom_line = []
            line_detail = []
            for lines in line.inquiry_line_ids:
                bom_line.append((0, 0, {
                    'bom_id': lines.bom_id.id,
                    'bom_cost': lines.bom_cost
                }))
            for liness in line.inquiry_line_detail:
                line_detail.append((0, 0, {
                    'product_id': liness.product_id.id,
                    'name': liness.name,
                    'specs': liness.specs,
                    'brand': liness.brand,
                    'unit_weight': liness.unit_weight,
                    'total_weight': liness.total_weight,
                    'product_uom_quantity': liness.product_uom_quantity,
                    'product_uom': liness.product_uom.id,
                    'product_uom_category_id': liness.product_uom_category_id.id,
                    'cost_price': liness.cost_price,
                    'due_date': liness.due_date,
                }))
            log_inq.create(
                {
                    'inquiry_id': int(line.id),
                    'name': f"{line.name} Revisi ({datetime.now()})",
                    'partner_id': line.partner_id.id,
                    'project_category': line.project_category,
                    'pic_user': line.pic_user.id,
                    'date': line.date,
                    'due_date': line.due_date,
                    'note': line.note,
                    'crm_state': line.crm_state,
                    'bom_line': bom_line,
                    'line_detail': line_detail,
                }
            )
            line.state = 'boq'

    def _compute_count_so(self):
        for line in self:
            sale_order = self.env['sale.order'].search(
                [('state', '=', 'sale'), ('opportunity_id', '=', int(line.opportunity_id.id))])
            line.count_so = 0
            if sale_order:
                line.count_so = len(sale_order)

    def action_so(self):
        pass

    def _compute_count_rfp(self):
        for line in self:
            line.count_rfp = 0
            request_price = self.env['request.price'].search([('inquiry_id', '=', int(line.id))])
            if request_price:
                line.count_rfp = len(request_price)

    def action_count_rfp(self):
        for line in self:
            result = {
                "type": "ir.actions.act_window",
                "res_model": "request.price",
                "domain": [('inquiry_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "RFP",
                'view_mode': 'tree,form',
            }
            return result

    def action_create_mo(self):
        for line in self:
            for lines in line.inquiry_line_ids:
                if lines.bom_id:
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', int(lines.bom_id.product_tmpl_id.id))])
                    self.env['mrp.production'].create({
                        'product_id': product_id.id,
                        'bom_id': int(lines.bom_id.id)
                    })

    # attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'inquiry.inquiry')],
    #                                  string='Attachments')
    def action_compute_material(self):
        for line in self:
            bom = self.env['mrp.bom'].search([('id', 'in', line.inquiry_line_ids.bom_id.ids)])
            if bom:
                bom_global = self.env['mrp.bom'].search([])
                bom_line = self.env['inquiry.line.detail'].search([('inquiry_id', '=', int(line.id))])
                bom_line.unlink()
                list_product = []
                for lines in bom:
                    for liness in lines.bom_line_ids:
                        if not any(
                                liness.product_id.product_tmpl_id.id == item.product_tmpl_id.id for item in bom_global):
                            # print(liness.product_id.product_tmpl_id.name)
                            desc = liness.product_id.product_tmpl_id.name
                            if liness.product_id.product_tmpl_id.description:
                                desc = liness.product_id.product_tmpl_id.description
                            if not any(item[2]['product_id'] == liness.product_id.id for item in list_product):
                                list_product.append((0, 0, {
                                    'product_id': liness.product_id.id,
                                    'name': str(desc),
                                    'product_uom_quantity': liness.product_qty,
                                    'cost_price': liness.product_id.product_tmpl_id.standard_price,
                                    'unit_weight': liness.product_id.product_tmpl_id.weight,
                                    'product_uom': liness.product_uom_id.id
                                }))
                            else:
                                for list_data in list_product:
                                    if list_data[2]['product_id'] == liness.product_id.id:
                                        list_data[2]['product_uom_quantity'] += liness.product_qty

                        # jika product memiliki BOM
                        if any(liness.product_id.product_tmpl_id.id == items.product_tmpl_id.id for items in
                               bom_global):
                            bom_line_kit = self.env['mrp.bom'].search(
                                [('product_tmpl_id', '=', liness.product_id.product_tmpl_id.id)])
                            if bom_line_kit:
                                if len(bom_line_kit) > 1:
                                    raise UserError('The product (' + str(
                                        bom_line_kit.product_tmpl_id.name) + ') bomb cannot be more than 1')
                                else:
                                    for line_kit in bom_line_kit.bom_line_ids:
                                        bom_line_kit2 = self.env['mrp.bom'].search(
                                            [('product_tmpl_id', '=', line_kit.product_id.product_tmpl_id.id)])
                                        if bom_line_kit2:
                                            if len(bom_line_kit2) > 1:
                                                raise UserError('The product (' + str(
                                                    bom_line_kit2.product_tmpl_id.name) + ') bomb cannot be more than 1')
                                            else:
                                                for line_kit2 in bom_line_kit2.bom_line_ids:
                                                    bom_line_kit3 = self.env['mrp.bom'].search(
                                                        [('product_tmpl_id', '=',
                                                          line_kit2.product_id.product_tmpl_id.id)])
                                                    if bom_line_kit3:
                                                        if len(bom_line_kit3) > 1:
                                                            raise UserError('The product (' + str(
                                                                bom_line_kit3.product_tmpl_id.name) + ') bomb cannot be more than 1')
                                                        else:
                                                            for line_kit3 in bom_line_kit3.bom_line_ids:
                                                                bom_line_kit4 = self.env['mrp.bom'].search(
                                                                    [('product_tmpl_id', '=',
                                                                      line_kit3.product_id.product_tmpl_id.id)])
                                                                if bom_line_kit4:
                                                                    if len(bom_line_kit4) > 1:
                                                                        raise UserError('The product (' + str(
                                                                            bom_line_kit4.product_tmpl_id.name) + ') bomb cannot be more than 1')
                                                                    else:
                                                                        for line_kit4 in bom_line_kit4.bom_line_ids:
                                                                            if not any(
                                                                                    line_kit4.product_id.product_tmpl_id.id == items.product_tmpl_id.id
                                                                                    for items in bom_global):
                                                                                description = line_kit4.product_id.product_tmpl_id.name
                                                                                if line_kit4.product_id.product_tmpl_id.description:
                                                                                    description = line_kit4.product_id.product_tmpl_id.description
                                                                                if not any(
                                                                                        line_kit4.product_id.id ==
                                                                                        item[2]['product_id']
                                                                                        for item in list_product):
                                                                                    list_product.append((0, 0, {
                                                                                        'product_id': line_kit4.product_id.id,
                                                                                        'name': str(description),
                                                                                        'product_uom_quantity': line_kit4.product_qty,
                                                                                        'cost_price': line_kit4.product_id.product_tmpl_id.standard_price,
                                                                                        'unit_weight': line_kit4.product_id.product_tmpl_id.weight,
                                                                                        'product_uom': line_kit4.product_uom_id.id
                                                                                    }))
                                                                                else:
                                                                                    for list_data in list_product:
                                                                                        if list_data[2][
                                                                                            'product_id'] == line_kit4.product_id.id:
                                                                                            list_data[2][
                                                                                                'product_uom_quantity'] += line_kit4.product_qty
                                                                if not any(
                                                                        line_kit3.product_id.product_tmpl_id.id == items.product_tmpl_id.id
                                                                        for items in bom_global):
                                                                    description = line_kit3.product_id.product_tmpl_id.name
                                                                    if line_kit3.product_id.product_tmpl_id.description:
                                                                        description = line_kit3.product_id.product_tmpl_id.description
                                                                    if not any(
                                                                            line_kit3.product_id.id == item[2][
                                                                                'product_id']
                                                                            for item in list_product):
                                                                        list_product.append((0, 0, {
                                                                            'product_id': line_kit3.product_id.id,
                                                                            'name': str(description),
                                                                            'product_uom_quantity': line_kit3.product_qty,
                                                                            'cost_price': line_kit3.product_id.product_tmpl_id.standard_price,
                                                                            'unit_weight': line_kit3.product_id.product_tmpl_id.weight,
                                                                            'product_uom': line_kit3.product_uom_id.id
                                                                        }))
                                                                    else:
                                                                        for list_data in list_product:
                                                                            if list_data[2][
                                                                                'product_id'] == line_kit3.product_id.id:
                                                                                list_data[2][
                                                                                    'product_uom_quantity'] += line_kit3.product_qty
                                                    if not any(
                                                            line_kit2.product_id.product_tmpl_id.id == items.product_tmpl_id.id
                                                            for items in bom_global):
                                                        description = line_kit2.product_id.product_tmpl_id.name
                                                        if line_kit2.product_id.product_tmpl_id.description:
                                                            description = line_kit2.product_id.product_tmpl_id.description
                                                        if not any(
                                                                line_kit2.product_id.id == item[2]['product_id']
                                                                for item in list_product):
                                                            list_product.append((0, 0, {
                                                                'product_id': line_kit2.product_id.id,
                                                                'name': str(description),
                                                                'product_uom_quantity': line_kit2.product_qty,
                                                                'cost_price': line_kit2.product_id.product_tmpl_id.standard_price,
                                                                'unit_weight': line_kit2.product_id.product_tmpl_id.weight,
                                                                'product_uom': line_kit2.product_uom_id.id
                                                            }))
                                                        else:
                                                            for list_data in list_product:
                                                                if list_data[2][
                                                                    'product_id'] == line_kit2.product_id.id:
                                                                    list_data[2][
                                                                        'product_uom_quantity'] += line_kit2.product_qty
                                        description = line_kit.product_id.product_tmpl_id.name
                                        if line_kit.product_id.product_tmpl_id.description:
                                            description = line_kit.product_id.product_tmpl_id.description
                                        if not any(
                                                line_kit.product_id.product_tmpl_id.id == items.product_tmpl_id.id for
                                                items in bom_global):
                                            if not any(line_kit.product_id.id == item[2]['product_id'] for item in
                                                       list_product):
                                                list_product.append((0, 0, {
                                                    'product_id': line_kit.product_id.id,
                                                    'name': str(description),
                                                    'product_uom_quantity': line_kit.product_qty,
                                                    'cost_price': line_kit.product_id.product_tmpl_id.standard_price,
                                                    'unit_weight': line_kit.product_id.product_tmpl_id.weight,
                                                    'product_uom': line_kit.product_uom_id.id
                                                }))
                                            else:
                                                for list_data in list_product:
                                                    if list_data[2]['product_id'] == line_kit.product_id.id:
                                                        list_data[2]['product_uom_quantity'] += line_kit.product_qty
                # print(list_product)
                # exit()
                # to_create = [(0, 0, item) for item in list_product]

                line.inquiry_line_detail = list_product
                line.message_post(body='Update Cost')
            # pass
            # line.inquiry_line_detail =

    def action_request_price(self):
        for line in self:
            list = []
            for lines in line.inquiry_line_detail:
                list.append((0, 0, {
                    'product_id': lines.product_id.id,
                    'description': lines.name,
                    'weight': lines.product_id.product_tmpl_id.weight,
                    'quantity': lines.product_uom_quantity,
                    'product_uom': lines.product_uom.id,
                    'cost_price': lines.cost_price
                }))
            return {
                'type': 'ir.actions.act_window',
                'name': 'Request Price',
                'res_model': 'request.price.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'inquiry_id': int(line.id),
                    'date': str(datetime.now()),
                    'due_date': line.due_date,
                    'default_project_category': line.project_category,
                    'request_line_ids': list
                }
            }
            # rp = self.env['request.price'].search([])
            # list_line = []
            # bom = self.env['mrp.bom.line'].search([('bom_id', 'in', line.inquiry_line_ids.bom_id.ids)])
            # # raise UserError(bom)
            # for boms in bom:
            #     product = self.env['product.product'].search(
            #         [('product_tmpl_id', 'in', line.inquiry_line_ids.bom_id.product_tmpl_id.ids)])
            #     if not any(boms.product_id.id == item.id for item in product):
            #         list_line.append((0, 0, {
            #             'product_id': boms.product_id.product_tmpl_id.id,
            #             'cost_price': float(boms.product_id.product_tmpl_id.standard_price)
            #         }))
            # data = {
            #     'inquiry_id': int(line.id),
            #     'date': datetime.now().strftime("%Y-%m-%d"),
            #     'request_line_ids': list_line
            # }
            # rp.create(data)
            # bom = self.env['inquiry.inquiry'].browse(int(line.id))
            # bom.write({'state': 'request'})

            # for lines in line.inquiry_line_ids:
            #     product = self.env['product.template'].search(
            #         [('id', '=', int(lines.product_tmpl_id.id)), ('standard_price', '=', 0)])
            #     if product:
            #         list_line.append((0, 0, {
            #             'product_id': lines.product_id.id
            #         }))
            #
            #     # else:
            #     #     raise UserError('Product not found')
            #
            # data = {
            #     'bom_id': int(line.id),
            #     'date': datetime.now().strftime("%Y-%m-%d"),
            #     'request_line_ids': list_line
            # }
            # # print(data)
            # # exit()
            # rp.create(data)
            # bom = self.env['mrp.bom'].browse(int(line.id))
            # bom.write({'request_state': True})

    def _compute_state_mrf(self):
        for line in self:
            mrf = self.env['mrf.mrf'].search([('inquiry_id', '=', int(line.id)), ('state', '!=', 'cancel')])
            line.state_material = False
            if mrf:
                line.state_material = True

    def get_data(self):
        return 1

    def action_compute_task(self):
        for line in self:
            # for line in self:
            new_line = self.env['inquiry.line.task'].search([])
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', line.opportunity_id.id), ('state', '=', 'sale')])
            # line.mrp_production_count = 0
            if so:
                mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
                for mos in mo:
                    task_line = self.env['inquiry.line.task'].search([('id', 'in', line.inquiry_line_task.ids)])
                    if task_line:
                        task_line.unlink()
                    new_line.create({
                        'inquiry_id': int(line.id),
                        'mo_id': int(mos.id),
                        'product_id': int(mos.product_id.id),
                        'production_ref': str(mos.product_id.product_tmpl_id.name)

                    })
                    sub_mo_ids = mos._get_children().ids
                    mo_task = self.env['mrp.production'].search([('id', 'in', sub_mo_ids)])
                    if mo_task:
                        for moss in mo_task:

                            new_line.create({
                                'inquiry_id': int(line.id),
                                'mo_id': int(moss.id),
                                'product_id': int(moss.product_id.id),
                                'production_ref': str(mos.product_id.product_tmpl_id.name)

                            })
                            mo_task2 = self.env['mrp.production'].search([('id', 'in', moss._get_children().ids)])
                            if mo_task2:
                                for task2 in mo_task2:
                                    new_line.create({
                                        'inquiry_id': int(line.id),
                                        'mo_id': int(task2.id),
                                        'product_id': int(task2.product_id.id),
                                        'production_ref': str(task2.product_id.product_tmpl_id.name)

                                    })
                                    mo_task3 = self.env['mrp.production'].search(
                                        [('id', 'in', task2._get_children().ids)])
                                    if mo_task3:
                                        for task3 in mo_task3:
                                            new_line.create({
                                                'inquiry_id': int(line.id),
                                                'mo_id': int(task3.id),
                                                'product_id': int(task3.product_id.id),
                                                'production_ref': str(task3.product_id.product_tmpl_id.name)

                                            })
                                            mo_task4 = self.env['mrp.production'].search(
                                                [('id', 'in', task3._get_children().ids)])
                                            if mo_task4:
                                                for task4 in mo_task4:
                                                    new_line.create({
                                                        'inquiry_id': int(line.id),
                                                        'mo_id': int(task4.id),
                                                        'product_id': int(task4.product_id.id),
                                                        'production_ref': str(task4.product_id.product_tmpl_id.name)
                                                    })

    def action_mrf(self):
        for line in self:
            if not line.due_date:
                raise UserError('Due Date is Mandatory Field')
            # for line in self:
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', line.opportunity_id.id), ('state', '=', 'sale')])
            # line.mrp_production_count = 0
            if so:
                mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
                for mos in mo:
                    sub_mo_ids = mos._get_children().ids
                    mo_task = self.env['mrp.production'].search([('id', 'in', sub_mo_ids)])
                    if mo_task:
                        task_line = self.env['inquiry.line.task'].search([('id', 'in', line.inquiry_line_task.ids)])
                        if task_line:
                            task_line.unlink()
                        for moss in mo_task:
                            new_line = self.env['inquiry.line.task'].search([])
                            new_line.create({
                                'inquiry_id': int(line.id),
                                'mo_id': int(moss.id),
                                'product_id': int(moss.product_id.id),
                                'production_ref': str(mos.product_id.product_tmpl_id.name)

                            })

                        # print('mo_task')
            # exit()
            list = []
            bom = self.env['mrp.bom'].search([('id', 'in', line.inquiry_line_ids.bom_id.ids)])
            # raise UserError(bom)
            public = self.env['mrp.bom'].search([])
            sale = self.env['sale.order'].search(
                [('opportunity_id', '=', int(line.opportunity_id.id)), ('state', '=', 'sale')])
            if sale:
                if len(sale) > 1:
                    raise UserError('Sale order more than 1')
                    exit()
                bom_line = self.env['mrp.bom.line'].search([('bom_id', 'in', bom.ids)])
                for lines in line.inquiry_line_detail:
                    # if not any(lines.product_tmpl_id.id == items.product_tmpl_id.id for items in bom):
                    # product = self.env['product.product'].search(
                    #     [('product_tmpl_id', '=', int(lines.product_tmpl_id.id))])
                    list.append((0, 0, {
                        'product_id': int(lines.product_id.id),
                        'type': str(line.project_category),
                        'quantity': lines.product_uom_quantity,
                        'product_uom': lines.product_uom.id,
                        'unit_weight': lines.unit_weight,
                        'description': str(lines.name),
                        'specs_detail': str(lines.specs),
                        'brand': str(lines.brand),
                        'unit_cost': lines.cost_price

                    }))
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Material Request',
                    'res_model': 'rfq.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'inquiry_id': int(line.id),
                        'partner_id': line.partner_id.id,
                        'sale_id': int(sale.id),
                        'due_date': str(line.due_date),
                        'rfq_line_ids': list
                    }
                }
            else:
                raise UserError('there are no sale orders !')
            # raise UserError(list)

    def action_count_mrf(self):
        for line in self:
            mrf = self.env['mrf.mrf'].search([('inquiry_id', '=', int(line.id))])
            list = len(mrf)
            if list == 1:
                # inquiry_record = self.env['inquiry.inquiry'].search([('opportunity_id', '=', int(line.id))],
                #                                                     limit=1)
                quotations = self.env['mrf.mrf'].search(
                    [('inquiry_id', '=', int(line.id))], limit=1)
                result = {
                    "type": "ir.actions.act_window",
                    "res_model": "mrf.mrf",
                    "domain": [('inquiry_id', '=', int(line.id))],
                    "context": {"create": False},
                    "name": "PO",
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': int(quotations.id)
                }

            elif list > 1:
                result = {
                    "type": "ir.actions.act_window",
                    "res_model": "mrf.mrf",
                    "domain": [('inquiry_id', '=', int(line.id))],
                    "context": {"create": False},
                    "name": "PO",
                    'view_mode': 'tree,form',
                }
            return result

    def action_update_state_boq(self):
        for line in self:
            inquiry = self.env['inquiry.inquiry'].browse(int(line.id))
            # for lines in line.inquiry_line_ids:
            #     if lines:
            inquiry.write({
                'state': 'boq'
            })

    def action_view_mrp_productions(self):
        for line in self:
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', line.opportunity_id.id), ('state', '=', 'sale')])
            mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
            sub_mo = self.env['mrp.production'].search([('id', 'in', mo._get_children().ids)])

            id = []
            if mo:
                for mos in mo:
                    id.append(int(mos.id))
            if sub_mo:
                for sub_mos in sub_mo:
                    id.append(int(sub_mos.id))
                    sub2_mo = self.env['mrp.production'].search([('id', 'in', sub_mos._get_children().ids)])
                    if sub2_mo:
                        for sub2_mos in sub2_mo:
                            id.append(int(sub2_mos.id))
                            sub3_mo = self.env['mrp.production'].search([('id', 'in', sub2_mos._get_children().ids)])
                            if sub3_mo:
                                for sub3_mos in sub3_mo:
                                    id.append(int(sub3_mos.id))
                                    sub4_mo = self.env['mrp.production'].search(
                                        [('id', 'in', sub3_mos._get_children().ids)])
                                    if sub4_mo:
                                        for sub4_mos in sub4_mo:
                                            id.append(int(sub4_mos.id))

            result = {
                "type": "ir.actions.act_window",
                "res_model": "mrp.production",
                "domain": [('id', 'in', id)],
                "context": {"create": False},
                "name": "Manufactur",
                'view_mode': 'tree,form',
            }
            return result

    def _compute_mo_count(self):
        for line in self:
            so = self.env['sale.order'].search(
                [('opportunity_id', '=', line.opportunity_id.id), ('state', '=', 'sale')])
            line.mrp_production_count = 0
            if so:
                mo = self.env['mrp.production'].search([('origin', '=', str(so.name))])
                # sub_mo = self.env['mrp.production'].search([('origin', '=', str(mo.name))])
                line.mrp_production_count = len(mo)

    def _compute_use_bom(self):
        for line in self:
            line.count_bom = 0
            bom = self.env['mrp.bom'].search([('inquiry_id', '=', int(line.id))])
            if bom:
                for i in bom:
                    print(i)
                    line.count_bom += 1

    def _compute_use_mrf(self):
        for line in self:
            line.count_mrf = 0
            mrf = self.env['mrf.mrf'].search([('inquiry_id', '=', int(line.id))])
            if mrf:
                jumlah = len(mrf)
                line.count_mrf = jumlah

    def action_create_bom(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create BOM',
            'res_model': 'mrp.bom',
            'view_type': 'form',
            'view_mode': 'form',
            # 'target': 'new',
            'context': {
                'inquiry_id': int(self.id),
            }
        }

    def action_count_bom(self):
        for line in self:
            result = {
                "type": "ir.actions.act_window",
                "res_model": "mrp.bom",
                "domain": [('inquiry_id', '=', int(line.id))],
                "context": {"create": False},
                "name": "BOM",
                'view_mode': 'tree,form',
            }
            return result
        # raise UserError('Test action BOM')

    def action_count_rfq(self):
        for line in self:
            if line.id:
                rfq = self.env['rfq.rfq'].search([('inquiry_id', '=', int(line.id))])
                if rfq:
                    result = {
                        "type": "ir.actions.act_window",
                        "res_model": "rfq.rfq",
                        "domain": [('inquiry_id', '=', int(line.id))],
                        "context": {"create": False},
                        "name": "RFQ",
                        'view_mode': 'tree,form',
                    }
                    return result
                else:
                    raise UserError('Data RFQ pada form ini tidak tersedia')

            else:
                raise UserError('ID Inquiry tidak ada!')

    def _compute_count_rfq(self):
        count = 0
        for line in self:
            rfq = self.env['rfq.rfq'].search([('inquiry_id', '=', int(line.id))])

            if rfq:
                # line.state = "rfq"
                for liness in rfq:
                    if liness.id:
                        count += 1
            line.count_rfq = int(count)

    def _compute_state_count(self):
        for line in self:
            line.state_count_rfq = False
            rfq = self.env['rfq.rfq'].search([('inquiry_id', '=', int(line.id))])
            if rfq:
                line.state_count_rfq = True

    def action_cancel(self):
        for line in self:
            inquiry = self.env['inquiry.inquiry'].browse(int(line.id))
            inquiry.write({
                'state': 'cancel'
            })

    def action_update_cost(self):
        for line in self:
            crm = self.env['crm.lead'].browse(int(line.opportunity_id.id))
            crm.write({
                'status_estimate': True,
            })
            # raise UserError(crm)
            for crms in crm:
                if hasattr(crms, 'x_review_result') and hasattr(crms, 'x_has_request_approval'):
                    crms.write({
                        'x_review_result': None,
                        'x_has_request_approval': None
                    })
            bom = self.env['mrp.bom'].search([('id', 'in', line.inquiry_line_ids.bom_id.ids)])
            bom_global = self.env['mrp.bom'].search([])
            product = self.env['product.product'].search([('product_tmpl_id', 'in', bom.product_tmpl_id.ids)])
            bom_line = self.env['mrp.bom.line'].search(
                [('bom_id', 'in', bom.ids), ('product_id', 'not in', product.ids)])
            # for boms in bom_line:
            #     if boms.product_id.product_tmpl_id.standard_price == 0:
            #         raise UserError('There is a material product price of 0 !!')
            #     else:
            #         continue
            lead_line_detail = self.env['lead.line.detail'].search([('lead_line_id', '=', line.opportunity_id.id)])
            if line.opportunity_id:
                line.opportunity_id.is_approve = False
            # if lead_line_detail:
            # if lead_line_detail:
            for cek in line.inquiry_line_detail:
                if cek.cost_price == 0:
                    raise UserError('There is a material product price of 0 !!')
            if line.project_category == 'project' or line.project_category == 'service':
                lead_line_detail.unlink()
                for line_detail in line.inquiry_line_detail:
                    self.env['lead.line.detail'].create({
                        'lead_line_id': int(line.opportunity_id.id),
                        'product_id': line_detail.product_id.id,
                        'name': line_detail.name,
                        'product_uom_quantity': line_detail.product_uom_quantity,
                        'product_uom': line_detail.product_uom.id,
                        'cost_price': line_detail.cost_price
                    })
            # else:
            #     for line_detail in line.inquiry_line_detail:
            #         if line_detail.cost_price == 0:
            #             raise UserError('There is a material product price of 0 !!')
            #         else:
            #             continue
            #         self.env['lead.line.detail'].create({
            #             'lead_line_id': int(line.opportunity_id.id),
            #             'product_id': line_detail.product_id.id,
            #             'name': line_detail.name,
            #             'product_uom_quantity': line_detail.product_uom_quantity,
            #             'product_uom': line_detail.product_uom.id,
            #             'cost_price': line_detail.cost_price
            #         })

            for lines in line.inquiry_line_ids:
                cost = 0
                for biaya in lines.bom_id.bom_line_ids:
                    # cost += product.cost_price * biaya.product_qty
                    if any(biaya.product_id.product_tmpl_id == item.product_tmpl_id for item in bom_global):
                        # print(biaya.product_id.product_tmpl_id.name)
                        sub_bom = self.env['mrp.bom'].search(
                            [('product_tmpl_id', '=', biaya.product_id.product_tmpl_id.id)])
                        if len(sub_bom) > 1:
                            raise UserError(
                                'Duplicate Bills of Materila for Product' + str(biaya.product_id.product_tmpl_id.name))
                        for subline in sub_bom.bom_line_ids:
                            product = self.env['inquiry.line.detail'].search(
                                [('inquiry_id', '=', int(line.id)), ('product_id', '=', int(subline.product_id.id))],
                                limit=1)
                            cost += product.cost_price * subline.product_qty
                            # print('any product' + subline.product_id.product_tmpl_id.name)
                    else:
                        # print('core bom'+biaya.product_id.product_tmpl_id.name)
                        product = self.env['inquiry.line.detail'].search(
                            [('inquiry_id', '=', int(line.id)), ('product_id', '=', int(biaya.product_id.id))],
                            limit=1)
                        cost += product.cost_price * biaya.product_qty
                inquiry_line = self.env['inquiry.line'].browse(lines.id)
                inquiry_line.write({
                    'bom_cost': float(line.total_amount)
                })
            lead_line = self.env['lead.line'].search([('lead_line_id', '=', line.opportunity_id.id)])

            if lead_line:
                lead_line.unlink()
                if line.project_category == 'project' or line.project_category == 'service':
                    for bom_lead in line.inquiry_line_ids:
                        if bom_lead.bom_id.product_tmpl_id.is_master:
                            # list_product_crm.append()
                            des = bom_lead.bom_id.product_tmpl_id.description
                            deskripsi = bom_lead.bom_id.product_tmpl_id.name
                            if des:
                                deskripsi = bom_lead.bom_id.product_tmpl_id.description
                            product_bom = self.env['product.product'].search(
                                [('product_tmpl_id', '=', bom_lead.bom_id.product_tmpl_id.id)])
                            self.env['lead.line'].create({
                                'lead_line_id': int(line.opportunity_id.id),
                                'product_id': product_bom.id,
                                'name': str(deskripsi),
                                'product_uom_quantity': bom_lead.bom_id.product_qty,
                                'product_uom': bom_lead.bom_id.product_uom_id.id,
                                'tax_id': product_bom.taxes_id or False,
                                'cost_price': bom_lead.bom_cost
                            })
                            crm = self.env['crm.lead'].browse(int(line.opportunity_id.id))
                            crm.write({
                                'cost_estimation': bom_lead.bom_cost * bom_lead.bom_id.product_qty
                            })
                elif line.project_category == 'supply':
                    for product_supply in line.inquiry_line_detail:
                        if product_supply.product_id.product_tmpl_id.is_master:
                            # list_product_crm.append()
                            des = product_supply.product_id.product_tmpl_id.description
                            deskripsi = product_supply.product_id.product_tmpl_id.name
                            if des:
                                deskripsi = product_supply.product_id.product_tmpl_id.description
                            product_bom = self.env['product.product'].search(
                                [('product_tmpl_id', '=', product_supply.product_id.product_tmpl_id.id)])
                            self.env['lead.line'].create({
                                'lead_line_id': int(line.opportunity_id.id),
                                'product_id': product_bom.id,
                                'name': str(deskripsi),
                                'product_uom_quantity': product_supply.product_uom_quantity,
                                'product_uom': product_supply.product_uom.id,
                                'tax_id': product_bom.taxes_id or False,
                                'cost_price': product_supply.cost_price
                            })
                    crm = self.env['crm.lead'].browse(int(line.opportunity_id.id))
                    subtotal = sum(line.inquiry_line_detail.mapped('subtotal'))
                    raise UserError(crm.cost_estimation)
                    crm.write({
                        'cost_estimation': float(subtotal)
                    })
            else:
                # raise UserError('product_bom')
                if line.project_category == 'project' or line.project_category == 'service':
                    for bom_lead in line.inquiry_line_ids:
                        if bom_lead.bom_id.product_tmpl_id.is_master:
                            # list_product_crm.append()
                            des = bom_lead.bom_id.product_tmpl_id.description
                            deskripsi = bom_lead.bom_id.product_tmpl_id.name
                            if des:
                                deskripsi = bom_lead.bom_id.product_tmpl_id.description
                            product_bom = self.env['product.product'].search(
                                [('product_tmpl_id', '=', bom_lead.bom_id.product_tmpl_id.id)])
                            self.env['lead.line'].create({
                                'lead_line_id': int(line.opportunity_id.id),
                                'product_id': product_bom.id,
                                'name': str(deskripsi),
                                'product_uom_quantity': bom_lead.bom_id.product_qty,
                                'product_uom': bom_lead.bom_id.product_uom_id.id,
                                'tax_id': product_bom.taxes_id or False,
                                'cost_price': bom_lead.bom_cost
                            })
                            crm = self.env['crm.lead'].browse(int(line.opportunity_id.id))
                            crm.write({
                                'cost_estimation': bom_lead.bom_cost * bom_lead.bom_id.product_qty
                            })
                elif line.project_category == 'supply':
                    # raise UserError(line.inquiry_line_detail)
                    for product_supply in line.inquiry_line_detail:
                        if product_supply.product_id.product_tmpl_id.is_master:
                            # list_product_crm.append()
                            des = product_supply.product_id.product_tmpl_id.description
                            deskripsi = product_supply.product_id.product_tmpl_id.name
                            if des:
                                deskripsi = product_supply.product_id.product_tmpl_id.description
                            product_bom = self.env['product.product'].search(
                                [('product_tmpl_id', '=', product_supply.product_id.product_tmpl_id.id)])
                            self.env['lead.line'].create({
                                'lead_line_id': int(line.opportunity_id.id),
                                'product_id': product_bom.id,
                                'name': str(deskripsi),
                                'product_uom_quantity': product_supply.product_uom_quantity,
                                'product_uom': product_supply.product_uom.id,
                                'tax_id': product_bom.taxes_id or False,
                                'cost_price': product_supply.cost_price
                            })
                    crm = self.env['crm.lead'].browse(int(line.opportunity_id.id))
                    subtotal = sum(line.inquiry_line_detail.mapped('subtotal'))
                    crm.write({
                        'cost_estimation': float(subtotal)
                    })

            inq = self.env['inquiry.inquiry'].browse(int(line.id))
            inq.write({'state': 'cost'})

    def action_create_rfq(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create RFQ',
            'res_model': 'rfq.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'partner_id': self.partner_id.id,
            }
        }

    def action_send_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        # self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        # mail_template = self._find_mail_template()
        # if mail_template and mail_template.lang:
        #     lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'inquiry.inquiry',
            'default_res_ids': self.ids,
            # 'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        vals['name'] = self.env['ir.sequence'].next_by_code('INQ') or '/'
        return super(InquirySales, self).create(vals)


class InquiryLine(models.Model):
    _name = 'inquiry.line'

    bom_id = fields.Many2one('mrp.bom')
    inquiry_id = fields.Many2one('inquiry.inquiry')
    bom_cost = fields.Float()
    kategory = fields.Selection([
        ('project', 'Project'),
        ('service', 'Service'),
        ('supply', 'Supply')
    ], related='inquiry_id.project_category')
    process_to = fields.Selection([
        ('purchase', 'Purchase'),
        ('engineering', 'Engineering')
    ], related='inquiry_id.process_to')
    state_mo = fields.Boolean(compute='_compute_state_mo')
    count_so = fields.Integer(related="inquiry_id.count_so")
    pic_akses = fields.Boolean(related="inquiry_id.pic_akses")

    def _compute_state_mo(self):
        for line in self:
            line.state_mo = False
            sale_order = self.env['sale.order'].search(
                [('state', '=', 'sale'), ('opportunity_id', '=', int(line.inquiry_id.opportunity_id.id))], limit=1)
            if sale_order:
                # bom = self.env['mrp.bom'].browse(int(line.bom_id.id))
                # if bom:
                product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', int(line.bom_id.product_tmpl_id.id))])
                mo = self.env['mrp.production'].search(
                    [('origin', '=', str(sale_order.name)), ('product_id', '=', int(product.id))])
                if mo:
                    line.state_mo = True
            # raise UserError(line.state_mo)

    def action_create_mo(self):
        for line in self:
            product = self.env['product.product'].search(
                [('product_tmpl_id', '=', int(line.bom_id.product_tmpl_id.id))])
            so = self.env['sale.order'].search([('opportunity_id', '=', line.inquiry_id.opportunity_id.id)])
            # mo = self.env['mrp.production'].search([])
            # create_mo = mo.create({
            #     'product_id': int(product.id),
            #     'product_qty': 1.0,
            #     'origin': str(so.name),
            #     'state': 'draft'
            # })
            # if create_mo:
            #     create_mo.action_confirm()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Manufactur Order',
                'res_model': 'manufactur.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'product_id': int(product.id),
                    'schedule_date': datetime.now(),
                    'product_qty': 1,
                    'origin': str(so.name),
                }
            }


class InquiryLineTask(models.Model):
    _name = 'inquiry.line.task'

    mo_id = fields.Many2one('mrp.production')
    product_id = fields.Many2one('product.product')
    production_ref = fields.Char()
    componen_status = fields.Char(compute='_compute_componen_state')
    task_state = fields.Selection([
        ('confirm', 'Comfirmed'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ], compute='_compute_state_task')
    inquiry_id = fields.Many2one('inquiry.inquiry')

    @api.depends('mo_id')
    def _compute_componen_state(self):
        for line in self:
            mo = self.env['mrp.production'].search([('id', '=', int(line.mo_id.id))])
            if mo:
                line.componen_status = str(mo.components_availability)

    def action_view_task(self):
        for line in self:
            return {
                "type": "ir.actions.act_window",
                "res_model": "mrp.production",
                "domain": [('id', '=', int(line.mo_id.id))],
                "context": {"create": False},
                "name": "Manufactur",
                'view_mode': 'form',
                'res_id': int(line.mo_id.id)
            }

    @api.depends('mo_id')
    def _compute_state_task(self):
        for line in self:
            mo = self.env['mrp.production'].search([('id', '=', int(line.mo_id.id))])
            if mo:
                if mo.state == 'confirmed':
                    line.task_state = 'confirm'
                elif mo.state == 'done':
                    line.task_state = 'done'
                elif mo.state == 'cancel':
                    line.task_state = 'cancel'


class InquiryLineDetail(models.Model):
    _name = 'inquiry.line.detail'

    inquiry_id = fields.Many2one('inquiry.inquiry')
    product_id = fields.Many2one('product.product')
    name = fields.Text(string='Description', required=True)
    specs = fields.Char()
    brand = fields.Char()
    unit_weight = fields.Float()
    total_weight = fields.Float(compute="_compute_weight", store=True)
    product_uom_quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True,
                                        default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    @api.onchange('product_id')
    def _compute_default_price(self):
        for line in self:
            line.cost_price = False
            line.unit_weight = False
            if line.product_id:
                line.cost_price = line.product_id.product_tmpl_id.standard_price
                line.unit_weight = line.product_id.product_tmpl_id.weight

    cost_price = fields.Float('Unit Price')
    due_date = fields.Datetime(compute="_compute_due_date")

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals', store=True,
        # currency_field=None,
    )

    @api.depends('unit_weight', 'product_uom_quantity')
    def _compute_weight(self):
        for line in self:
            total = line.product_uom_quantity * line.unit_weight
            line.total_weight = total

    @api.depends('inquiry_id.due_date')
    def _compute_due_date(self):
        for line in self:
            line.due_date = False
            if line.inquiry_id.due_date:
                line.due_date = line.inquiry_id.due_date

    @api.depends('product_uom_quantity', 'cost_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.product_uom_quantity * line.cost_price
            line.subtotal = subtotal


class ResCustomer(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        # Membuat record baru dan menyimpannya
        new_record = super(ResCustomer, self).create(vals)

        # Mendapatkan ID dari record yang baru dibuat
        # rank = new_record.customer_rank
        # value = new_record.name
        # newname = value.isupper()
        new_record.name = new_record.name.upper()
        #
        # raise UserError(newname)

        # if rank > 0:
        #     if not all(c.isupper() for c in value if c.isalpha()):
        #         raise UserError('Nama Harus Menggunakan Huruf Kapital')

        return new_record  # Kembalikan record baru jika diperlukan
        # value = vals.get('name')
        # rank = vals.get('id')
        #
        # super(ResCustomer, self).create(vals)
        # raise UserError(rank)
        # exit()
        # if rank > 0:
        #     if not all(c.isupper() for c in value if c.isalpha()):
        #         raise UserError('Nama Harus Menggunakan Huruf Kapital')
        #
        # return True


class ProductInherith(models.Model):
    _inherit = 'product.template'

    is_master = fields.Boolean()
    is_it_assets = fields.Boolean()
    edit_cost = fields.Boolean(cmpute="_compute_edit_cost", default=False)

    # users_branch = fields.Char(compute="branch", search="branch_search")
    #
    # def branch(self):
    #     id = self.env.uid
    #     self.users_branch = self.env['res.users'].search([('id', '=', id)])
    #
    # def branch_search(self, operator, value):
    #     # for i in self:
    #     if self.env.uid == 16 or self.env.uid == 26 or self.env.uid == 14:
    #         contract = self.env['hr.contract'].search([('akses', '!=', True)])
    #         employee = self.env['hr.employee'].search([('id', 'in', contract.employee_id.ids)])
    #         # print('lihat employee', contract.id)
    #         domain = [('id', 'in', employee.ids)]
    #         return domain

    @api.model
    def create(self, vals):
        # if vals.get('name', '/') == '/':
        # raise UserError('test func')
        value = vals.get('name')
        vals['name'] = vals['name'].upper()
        # if not all(c.isupper() for c in value if c.isalpha()):
        #     raise UserError('Nama Harus Menggunakan Huruf Kapital')
        return super(ProductInherith, self).create(vals)

    def _compute_edit_cost(self):
        for line in self:
            user_id = self.env.uid
            user_login = self.env['res.users'].browse(user_id)
            if user_login:
                if user_login.is_purchase:
                    line.edit_cost = True
            else:
                line.edit_cost = False


class LogInquiry(models.Model):
    _name = 'log.inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Log Inquiry'

    inquiry_id = fields.Many2one('inquiry.inquiry')
    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    project_category = fields.Char()
    pic_user = fields.Many2one('res.users')
    date = fields.Date()
    due_date = fields.Date()
    note = fields.Text()
    crm_state = fields.Char()
    bom_line = fields.One2many('bom.line.log', 'inquiry_id')
    line_detail = fields.One2many('line.detail.log', 'inquiry_id')


class LogBomLine(models.Model):
    _name = 'bom.line.log'

    bom_id = fields.Many2one('mrp.bom')
    bom_cost = fields.Float()
    inquiry_id = fields.Many2one('log.inquiry')


class LineDetailLog(models.Model):
    _name = 'line.detail.log'

    inquiry_id = fields.Many2one('log.inquiry')
    product_id = fields.Many2one('product.product')
    name = fields.Text(string='Description', required=True)
    specs = fields.Char()
    brand = fields.Char()
    unit_weight = fields.Float()
    total_weight = fields.Float()
    product_uom_quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True,
                                        default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    cost_price = fields.Float('Unit Price')
    due_date = fields.Datetime()

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals', store=True,
    )

    @api.depends('product_uom_quantity', 'cost_price')
    def _compute_totals(self):
        for line in self:
            # if line.display_type != 'product':
            #     line.price_total = line.price_subtotal = False
            # # Compute 'price_subtotal'.
            # line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.product_uom_quantity * line.cost_price
            line.subtotal = subtotal
